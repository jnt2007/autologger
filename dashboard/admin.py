from django.contrib import admin
from datetime import datetime

# Register your models here.
from dashboard.models import Version, Panel, Feature, AutomationResult, FeatureMatching


class FeatureAdmin(admin.ModelAdmin):
    list_display = ('version', 'panel')
    filter_horizontal = ('feature',)
    save_as = True


class AutomationAdmin(admin.ModelAdmin):
    list_display = ('version', 'panel', 'feature', 'start_time')
    list_filter = ('version', 'panel')


admin.site.register(Version)
admin.site.register(Panel)
admin.site.register(Feature)
admin.site.register(AutomationResult, AutomationAdmin)
admin.site.register(FeatureMatching, FeatureAdmin)
