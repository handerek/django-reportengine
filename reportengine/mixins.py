from django.db.models.aggregates import Aggregate
from types import StringType, UnicodeType, FunctionType


class ExtendedQuerySetReportMixin(object):
    """
    ExtendedQuerySetReportMixin can be used together with all subclasses of
    QuerySetReport. It enables you to define repots by setting it's lables more 
    readable and collect values by model fields, related model fields, aggregates
    and computed by callbacks.
    
    e.g.
    
    def get_member_age(obj):
        return obj.date_joined - datetime.datetime.now()
    
    class TestReport(ExtendedQuerySetReportMixin, QuerySetReport):
        verbose_name = 'Test Report'
        slug = 'test-report'
        namespace = 'system'
        description = u'This is a test report demonstrating the usage of ExtendedQuerySetReportMixin'
        list_filter = ['date_joined', ]
        per_page = 500
        queryset = User.objects.filter(active=True)
        report = (
            ('ID'                   , 'id'),
            ('User profile ID'      , 'profile__id'),
            ('Amount of profiles'   , Count('profile')),
            ('Users age'            , get_member_age),
        )
    reportengine.register(TestReport)
    """
    _params = None
    _aggregates = None
    _property_names = None
    report = None
    
    def __init__(self, *args, **kwargs):
        self._params = kwargs.pop('params', None)
    
    @property
    def labels(self):
        return [ k for k, v in self.report ]
            
    def get_property_names(self):
        if not self._property_names:
            self._property_names = [ v for k, v in self.report if type(v) in [StringType, UnicodeType] ]
        return tuple(self._property_names)
    
    def get_aggregates(self):
        if not self._aggregates:
            self._aggregates = dict([ (k, v) for k, v in self.report if isinstance(v, Aggregate)])
        return self._aggregates
    
    def get_aggregate_names(self):
        return tuple(self.get_aggregates().keys())
    
    def get_queryset(self, filters, order_by, queryset=None):
        qs = super(ExtendedQuerySetReportMixin, self).get_queryset(filters, order_by, queryset)
        if self.get_aggregates():
            qs = qs.annotate(**self.get_aggregates())
        return qs
    
    def get_rows(self, filters={}, order_by=None):
        rows = []
        qs = self.get_queryset(filters, order_by)
        labels = self.get_property_names() + self.get_aggregate_names()
        
        for obj in qs:
            values = qs.filter(id=obj.id).values(*labels)[0]
            row = []
            
            for k, v in self.report:
                if type(v) is FunctionType:
                    row.append( v(obj) )
                elif type(v) in [StringType, UnicodeType]:
                    row.append( values[v] )
                elif isinstance(v, Aggregate):
                    row.append( getattr(obj, k) )
                else:
                    raise TypeError
                
            rows.append(tuple(row))

        return rows, (("total",qs.count()), )
