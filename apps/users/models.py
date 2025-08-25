from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal

class User(AbstractUser):
    email = models.EmailField(unique=True)
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_invested = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_received = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        if self.student_id:
            return f"{self.username} ({self.student_id})"
        return self.username

    @property
    def current_valuation(self):
        return self.total_received

    @property
    def ownership_percentage(self):
        if self.total_received > 0:
            return (self.total_invested / self.total_received) * 100
        return 0