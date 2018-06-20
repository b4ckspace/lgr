from itertools import chain, islice
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse, path
from django.utils.html import format_html, format_html_join
from lgr import models, forms
from typing import List

admin.site.site_header = 'Inventory'
admin.site.index_title = 'Inventory Administration'


@admin.register(models.Barcode)
class BarcodeAdmin(admin.ModelAdmin):
    autocomplete_fields = ('item', 'owner', 'parent')
    search_fields = ('code', 'item__name', 'description', 'owner__nickname')
    list_display = ('__str__', 'search_parent', 'search_children', 'buttons')
    list_filter = ('owner', 'item',)
    change_list_template = 'admin/custom_change_list.html'
    readonly_fields = ('code', )
    actions = ('move_multiple', )

    def save_model(self, request, obj, form, change):
        user = request.user.username
        user = models.Person.objects.get(nickname=user)
        obj.save(user=user)

    def short_description(self, obj: models.Loan):
        description = obj.description
        description = description.replace('\n', ' ')
        if len(description) > 15:
            description = '%s...' % description[:15]
        description = format_html(
            '<span title="{}">{}</span>',
            obj.description,
            description
        )
        return description
    short_description.short_description = 'Description'

    def search_parent(self, obj: models.Barcode):
        parent = format_html(
            '<a href="{}?q=code:{}">{}</a>',
            reverse('admin:lgr_barcode_changelist'),
            obj.parent.code if obj.parent else None,
            str(obj.parent),
        )
        return parent
    search_parent.short_description = 'Parent'

    def search_children(self, obj: models.Barcode):
        count = obj.children.count()
        parent = format_html(
            '<a href="{}?q=parent:{}">{} children</a>',
            reverse('admin:lgr_barcode_changelist'),
            obj.code,
            count,
        )
        return parent
    search_children.short_description = 'Children'

    def buttons(self, obj: models.Loan):
        actions = (
            ('admin:lgr_barcode_quickadd_for_barcode', 'Quickadd here'),
            ('admin:lgr_barcode_move_for_barcode', 'Move'),
            ('admin:lgr_barcode_moveinto_for_barcode', 'Move Into'),
        )
        actions = format_html_join(
            '\n', '<a class="button" href="{}">{}</a>',
            ((reverse(url, args=[obj.pk]), title) for url, title in actions)
        )
        return actions
    buttons.short_description = 'Actions'

    def quickadd_view(self, request, obj_id=None, *args, **kwargs):
        """Custom view for the quickadd button in admin."""
        if request.method != 'POST':
            form = forms.BarcodeQuickaddForm()
            if obj_id is not None:
                obj = models.Barcode.objects.get(pk=obj_id)
                form.fields['barcodes'].initial = ('# %s\n%s\n--'
                                                   % (obj.owner.nickname,
                                                      obj.pk))
        else:
            form = forms.BarcodeQuickaddForm(request.POST)
            if form.is_valid():
                BarcodeAdmin.process_quickadd(request,
                                              form.cleaned_data['barcodes'])

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Quickadd barcodes',
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/custom_change_form.html',
                                context=context)

    def moveinto_vew(self, request, obj_id, *args, **kwargs):
        """Custom view to move barcodes in selected barcode."""
        obj = models.Barcode.objects.get(pk=obj_id)

        if request.method != 'POST':
            form = forms.BarcodeMoveintoForm()
        else:
            form = forms.BarcodeMoveintoForm(request.POST)
            if form.is_valid():
                BarcodeAdmin.process_moveinto(request,
                                              form.cleaned_data['barcodes'],
                                              obj)

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Move barcodes into',
            'opts': self.model._meta,
            'before_form_text': {
                'text': f'All entered barcodes will be moved into "{obj}"',
            }
        }
        return TemplateResponse(request, 'admin/custom_change_form.html',
                                context=context)

    def move_multiple(self, request, queryset):
        """Custom view to move multiple barcodes to another parent."""
        ParentForm = self.get_form(request, queryset, change=True, fields=('parent', ))
        if request.method != 'POST':
            return redirect(reverse('admin:lgr_barcode_changelist'))
        if 'apply' not in request.POST:
            form = ParentForm(request.POST)
            form = forms.move_multiple_inject(form)

            before_form_text = dict()
            before_form_text['text'] = 'The following items will be moved:'
            before_form_text['list'] = queryset.all()

            context = {
                **self.admin_site.each_context(request),
                'opts': self.model._meta,
                'form': form,
                'media': self.media + form.media,
                'before_form_text': before_form_text,
                'title': 'Move multiple barcodes',
            }
            return TemplateResponse(request, 'admin/custom_change_form.html',
                                    context=context)
        form = ParentForm(request.POST)
        if form.is_valid():
            user = request.user.username
            user = models.Person.objects.get(nickname=user)
            parent = form.cleaned_data['parent']

            for barcode in queryset.all():
                if not parent in barcode.all_children:
                    barcode.parent = parent
                    barcode.save(user=user)
                    messages.info(
                        request,
                        '%s has now as parent %s' % (barcode, barcode.parent)
                    )
                else:
                    messages.error(
                        request,
                        '%s can\'t be a parent of %s' % (barcode, barcode.parent)
                    )
            return redirect(reverse('admin:lgr_barcode_changelist'))

    def move_view(self, request, *args, obj_id=None, **kwargs):
        """Custom view to move to another parent."""
        obj = None
        if obj_id is not None:
            obj = models.Barcode.objects.get(pk=obj_id)

        ParentForm = self.get_form(request, obj, change=True, fields=('parent', ))
        if request.method != 'POST':
            form = ParentForm(instance=obj)
        else:
            form = ParentForm(request.POST)
            if form.is_valid():
                user = request.user.username
                user = models.Person.objects.get(nickname=user)
                parent = form.cleaned_data['parent']
                obj.parent = parent
                obj.save(user=user)
                messages.info(request, '%s has now as parent %s' % (obj, obj.parent))
                return redirect(reverse('admin:lgr_barcode_changelist'))

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'form': form,
            'media': self.media + form.media,
            'title': 'Move barcode',
        }
        return TemplateResponse(request, 'admin/custom_change_form.html',
                                context=context)

    @staticmethod
    def process_quickadd(request, barcodes: list, parent=None):
        """Recursive creation of Barcodes form nested dicts."""
        for barcode in barcodes:
            parent = None
            if barcode.parent:
                parent = models.Barcode.objects.filter(code=barcode.parent).first()

            item, item_new = models.Item.objects.get_or_create(name=barcode.item)
            if item_new:
                messages.info(request, 'Item %s created.' % item)

            owner, owner_new = models.Person.objects.get_or_create(nickname=barcode.owner)
            if owner_new:
                messages.info(request, 'Person %s created.' % owner)

            if not isinstance(barcode, models.Barcode):
                barcode = models.Barcode(code=barcode.code,
                                         description=barcode.description,
                                         item=item, owner=owner, parent=parent)
                barcode.save()
                messages.info(request, 'Barcode %s created.' % barcode)

    @staticmethod
    def process_moveinto(request, barcodes: list, parent):
        """Move a list of barcodes into parent."""
        for barcode in barcodes:
            if not barcode:
                continue
            oldparent = barcode.parent
            barcode.parent = parent
            barcode.save()
            messages.info(request, f'{barcode} moved into {parent} from {oldparent}')

    def changelist_view(self, request, extra_context={}):
        topbuttons = [
            {'url': reverse('admin:lgr_barcode_quickadd'),
             'title': 'Quickadd'}
        ]
        extra_context.update({
            'topbuttons': topbuttons
        })
        return super().changelist_view(request, extra_context=extra_context)

    def get_changeform_initial_data(self, request):
        return {'owner': models.Person.objects.first()}

    def get_search_results(self, request, queryset, search_term: str):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term.startswith('code:'):
            queryset |= self.model.objects.filter(code=search_term[5:])
        if search_term.startswith('parent:'):
            queryset |= self.model.objects.filter(parent__code=search_term[7:])
        return queryset, use_distinct

    def get_urls(self):
        urls = super().get_urls()
        urls += [
            path('quickadd',
                 self.admin_site.admin_view(self.quickadd_view),
                 name='lgr_barcode_quickadd'),
            path('<str:obj_id>/quickadd',
                 self.admin_site.admin_view(self.quickadd_view),
                 name='lgr_barcode_quickadd_for_barcode'),
            path('<str:obj_id>/moveinto',
                 self.admin_site.admin_view(self.moveinto_vew),
                 name='lgr_barcode_moveinto_for_barcode'),
            path('<str:obj_id>/move',
                 self.admin_site.admin_view(self.move_view),
                 name='lgr_barcode_move_for_barcode'),
        ]
        return urls


class BarcodeInline(admin.TabularInline):
    model = models.Barcode
    autocomplete_fields = ('owner', )

    def get_formset(self, request, obj, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['owner'].initial = models.Person.objects.first()
        return formset


@admin.register(models.History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ('person', 'message', 'count')
    actions = None

    def count(self, obj: models.History):
        return obj.affected.count()
    count.short_description = 'Affected barcodes'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'count')
    autocomplete_fields = ('tags', )
    search_fields = ('name', )
    inlines = (BarcodeInline, )
    actions = ('merge_newest', 'merge_oldest')

    def count(self, obj):
        return obj.barcodes.count()

    def merge_oldest(self, request, queryset):
        queryset = queryset.order_by('pk')
        self.merge(request, queryset)
    merge_oldest.short_description = 'Merge barcodes -> oldest item'

    def merge_newest(self, request, queryset):
        queryset = queryset.order_by('-pk')
        self.merge(request, queryset)
    merge_newest.short_description = 'Merge barcodes -> newest item'

    def merge(self, request, queryset):
        """Merge barcodes from multiple items in to the first one in the
           queryset."""
        user = request.user.username
        user = models.Person.objects.get(nickname=user)

        new, *items = queryset.all()
        for old in items:
            barcodes = old.barcodes.all()
            count = 0
            for count, barcode in enumerate(barcodes, 1):
                barcode.item = new
                barcode.save(user=user)
            messages.info(
                request,
                'Moved %s items from %s to %s' % (count, old, new)
            )
            old.delete()


@admin.register(models.Loan)
class LoanAdmin(admin.ModelAdmin):
    autocomplete_fields = ('person', 'barcodes')
    list_display = ('__str__', 'taken_date', 'returned_date', 'item_count',
                    'buttons')
    readonly_fields = ('taken_date', 'returned_date', 'status')

    def buttons(self, obj: models.Loan):
        return format_html(
            '<a class="button" href="{r}">Return</a>',
            r=reverse('admin:lgr_loan_return', args=[obj.pk])
        )
    buttons.short_description = 'Actions'
    buttons.allow_tags = True

    def item_count(self, obj: models.Loan):
        """Number of barcodes for this item."""
        return obj.barcodes.count()
    item_count.short_description = 'Items'

    def return_view(self, request, object_id: int, *args, **kwargs):
        """Custom view to return a loan."""
        loan = self.get_object(request, object_id)
        if loan.status == models.Loan.RETURNED:
            messages.info(request, '%s has already been returned.' % loan)
            return redirect(reverse('admin:lgr_loan_changelist'))

        if request.method != 'POST':
            form = forms.ReturnForm(loan=loan)
        else:
            form = forms.ReturnForm(request.POST, loan=loan)
            if form.is_valid():
                items = models.Barcode.objects.filter(
                    code__in=form.cleaned_data['items']
                )
                self.process_return(request, loan, items)
                loan.status = models.Loan.RETURNED
                loan.save()
                return redirect(reverse('admin:lgr_loan_changelist'))

        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta
        context['form'] = form
        context['title'] = 'Return item'
        return TemplateResponse(request, 'admin/custom_change_form.html', context=context)

    def process_return(self, request, loan: models.Loan, barcodes: List[models.Barcode]):
        """Called from the return view, updates the loans as specified."""
        missing_items = list()
        returned_items = list()
        for barcode in loan.barcodes.all():
            if barcode not in barcodes:
                missing_items.append(barcode)
            else:
                returned_items.append(barcode)

        if missing_items:
            loan.barcodes.set(returned_items)

            leftover_loan = models.Loan.objects.create(person=loan.person)
            leftover_loan.barcodes.set(missing_items)
            messages.info(
                request, 'Created new loan for %s with %s'
                % (loan.person, ', '.join(str(i) for i in missing_items))
            )

    def get_urls(self):
        urls = super().get_urls()
        urls += [
            path('<int:object_id>/return',
                 self.admin_site.admin_view(self.return_view),
                 name='lgr_loan_return'),
        ]
        return urls


@admin.register(models.Person)
class PersonAdmin(admin.ModelAdmin):
    search_fields = ('nickname', 'firstname', 'lastname', 'email')


@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ('name', )
