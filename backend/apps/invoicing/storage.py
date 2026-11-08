from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateInvoiceStorage(FileSystemStorage):
    @property
    def location(self):
        return str(settings.PRIVATE_INVOICE_ROOT)

    @property
    def base_url(self):
        return None


private_invoice_storage = PrivateInvoiceStorage()
