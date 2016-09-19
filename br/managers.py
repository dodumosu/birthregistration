from django.db import models
from unicefng.br.querysets import SearchableLocationQuerySet


class BirthRegistrationManager(models.Manager):
    def get_query_set(self):
        return SearchableLocationQuerySet(self.model)
