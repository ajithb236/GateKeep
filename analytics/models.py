from django.db import models

class RequestLog(models.Model):
    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=100)
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    user_agent = models.CharField(max_length=300)
    referrer = models.CharField(max_length=300, blank=True, null=True)  # know where they came from
    response_time = models.FloatField()  # Time taken to respond in milliseconds
    timestamp = models.DateTimeField(auto_now_add=True)
    http_status = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),#improve query performance on timestamp
            models.Index(fields=["ip_address"]),
            models.Index(fields=["path"]),
        ]

    def __str__(self):
        return f"{self.ip_address} - {self.path} - {self.http_status}"
    
class BlockedCountry(models.Model):
    country_name = models.CharField(max_length=100, unique=True)
    reason = models.CharField(max_length=200, blank=True, null=True)
    blocked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.country_name