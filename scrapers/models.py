from django.db import models

class ScraperLog(models.Model):
    scraper_id = models.CharField(max_length=100)
    scraper_name = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)
    items_processed = models.IntegerField(default=0)
    items_created = models.IntegerField(default=0)
    items_updated = models.IntegerField(default=0)
    items_failed = models.IntegerField(default=0)
    success = models.BooleanField(default=True)
    message = models.TextField(blank=True, null=True)
    error_details = models.TextField(blank=True, null=True)
    execution_time = models.FloatField(null=True, blank=True)  # tiempo en segundos
    
    class Meta:
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.scraper_name} - {self.timestamp}"