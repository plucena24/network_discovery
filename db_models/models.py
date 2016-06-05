from django.db import models

class Credentials(models.Model):
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return '%s' % (self.username)

class SnmpCredentials(models.Model):
    community = models.CharField(max_length=50, blank=True, null=True)
    snmp_version = models.CharField(max_length=50, blank=True, null=True)
    snmp_username = models.CharField(max_length=50, blank=True, null=True)
    snmp_password = models.CharField(max_length=50, blank=True, null=True)
    encryption_password  = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return '%s' % (self.description)

class NetworkDevice(models.Model):
    device_name = models.CharField(primary_key=True, max_length=80)
    ip_address = models.GenericIPAddressField(protocol='IPv4')
    ipv6_address = models.GenericIPAddressField(protocol='IPv6',
                                                blank=True, null=True)
    device_class = models.CharField(max_length=50)
    ssh_port = models.IntegerField(blank=True, null=True)
    vendor = models.CharField(max_length=50, blank=True, null=True)
    model = models.CharField(max_length=50, blank=True, null=True)
    device_type = models.CharField(max_length=50, blank=True, null=True)
    os_version = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=50, blank=True, null=True)
    uptime_seconds = models.IntegerField(blank=True, null=True)
    credentials = models.ForeignKey(Credentials, blank=True, null=True)
    snmp_credentials = models.ForeignKey(SnmpCredentials, blank=True,
                                                          null=True)
    snmp_port = models.IntegerField(blank=True, null=True)
    cfg_file = models.CharField(max_length=100, blank=True, null=True)
    domain = models.CharField(max_length=100, blank=True, null=True)
    tags = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return '%s' % (self.device_name)
