from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import mark_safe
from django.db import models
from django.contrib import messages
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

from lgr.mixin import BarcodeHistoryMixin

from PIL import Image
from io import BytesIO
import sys

class Tag(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Person(models.Model):
    nickname = models.CharField(max_length=64)
    firstname = models.CharField(max_length=64, default='', blank=True)
    lastname = models.CharField(max_length=64, default='', blank=True)
    email = models.EmailField(default='', blank=True)

    def __str__(self):
        return "%s" % (self.nickname)


class Item(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    image = models.ImageField(upload_to=settings.MEDIA_ITEM_PATH, null=True, blank=True)

    def __str__(self):
        return self.name

    def image_tag(self):
        return mark_safe('<img src="%s" width="%s" height="%s" />' % (self.image.url, self.image.width, self.image.height))
    image_tag.short_description = 'Image Preview'

    # adapted from: https://djangosnippets.org/snippets/10597/
    def save(self):
        if self.image:
            #Opening the uploaded image
            im = Image.open(self.image)

            output = BytesIO()

            #Resize/modify the image
            max_height = im.height
            max_width = im.width
            if(settings.MEDIA_ITEM_MAX_HEIGHT > 0):
                max_height = settings.MEDIA_ITEM_MAX_HEIGHT
            if(settings.MEDIA_ITEM_MAX_WIDTH > 0):
                max_width = settings.MEDIA_ITEM_MAX_WIDTH

            if (max_height != im.height) or (max_width != im.width):
                im.thumbnail((max_width, max_height))

                #after modifications, save it to the output
                im.save(output, format='JPEG', quality=settings.MEDIA_ITEM_JPEG_QUALITY)
                output.seek(0)

                #change the imagefield value to be the newley modifed image value
                self.image = InMemoryUploadedFile(output,'ImageField', "%s.jpg" %self.image.name.split('.')[0], 'image/jpeg', sys.getsizeof(output), None)

        super(Item,self).save()


class Barcode(BarcodeHistoryMixin, models.Model):
    code = models.CharField(max_length=64, primary_key=True, unique=True,
                            editable=True)
    owner = models.ForeignKey(Person, related_name='barcodes',
                              on_delete=models.CASCADE, default=None, null=True)
    description = models.TextField(blank=True, default='')
    item = models.ForeignKey(Item, related_name='barcodes',
                             on_delete=models.CASCADE)
    parent = models.ForeignKey('self', related_name='children',
                               on_delete=models.SET_NULL, blank=True,
                               null=True, default=None)

    @cached_property
    def all_children(self):
        """Get all childs (recursive, including self)."""
        children = list()
        children.append(self)
        for child in self.children.all():
            for childchild in child.all_children:
                children.append(childchild)
        return children

    @cached_property
    def status(self):
        if self.loans and self.loans.filter(status=Loan.TAKEN).count():
            return 'taken'
        return 'stock'
    status.short_description = 'Status'

    @cached_property
    def api_parent_names(self):
        """Get a list of all parents."""
        parent = self.parent
        parents = list()
        while parent:
            if parent in parents:
                break
            parents.insert(0, parent)
            parent = parent.parent
        parents = [{'name': str(p), 'code': p.code} for p in parents]
        return parents

    @cached_property
    def api_child_names(self):
        """Get a list of all childs."""
        return [{'name': str(c), 'code': c.code} for c in self.children.all()]

    @cached_property
    def api_loan_info(self):
        """Return loan info."""
        loan = self.loans.filter(status='taken').first()
        if loan:
            return {'loan': True, 'person': loan.person.nickname}
        return {'loan': False}

    @cached_property
    def api_history(self):
        history = self.history.all().order_by('-pk')[:10]
        history = [
            {
                'user': h.person.nickname,
                'field': h.field,
                'old': h.old,
                'new': h.new,
            }
            for h in history
        ]
        return history

    def save(self, *args, **kwargs):
        self.code = self.code.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return '%s (%s)' % (self.item.name, self.code)


class History(models.Model):
    message = models.CharField(max_length=1024)
    affected = models.ManyToManyField(Barcode, related_name='history')
    person = models.ForeignKey(Person, on_delete=models.CASCADE,
                               related_name='changes')

    def __str__(self):
        return f'{self.person.nickname}: {self.message}'

    class Meta:
        verbose_name_plural = 'Histories'


class Loan(models.Model):
    TAKEN = 'taken'
    RETURNED = 'returned'
    STATUS_CHOICES = (
        (TAKEN, 'taken'),
        (RETURNED, 'returned')
    )

    person = models.ForeignKey(Person, related_name='loans',
                               on_delete=models.PROTECT)
    barcodes = models.ManyToManyField(Barcode, related_name='loans')
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, default=TAKEN, choices=STATUS_CHOICES)
    taken_date = models.DateTimeField()
    return_date = models.DateTimeField(blank=True, null=True)
    returned_date = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.taken_date = timezone.now()
        if self.status == self.RETURNED and not self.returned_date:
            self.returned_date = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return "Loan to %s" % self.person
