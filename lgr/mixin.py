from lgr import models


class BarcodeHistoryMixin():
    """Mixin to track the history of changes on a model."""

    def diff(self):
        """Return all fields that have been changed as dict."""
        old_obj = type(self).objects.get(pk=self.pk)
        self._old = {
            f.name: getattr(self, f.name, None)
            for f in self._meta.fields
        }
        for field in self._meta.fields:
            field = field.name
            new = getattr(self, field)
            old = getattr(old_obj, field)
            if old != new:
                yield field, old, new

    def save(self, *args, user=None, **kwargs):
        if user:
            # find changes and write them to history
            for field, old, new in self.diff():
                message = f'changed {field} of {self.code} from "{old}" to "{new}"'
                history = models.History(person=user, message=message)
                history.save()

                # track parent changes for all children
                if field == 'parent':
                    history.affected.set(self.all_children)
                else:
                    history.affected.set([self])
        super().save(*args, **kwargs)
