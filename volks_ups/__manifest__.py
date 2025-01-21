{
    'name' : 'Management System',
    'author' : 'apocalypse',
    'summary' : 'Quotation Sales',
    'depends' : ['mail'],
    'sequence' : -1000,
    'data' :[
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/sales.xml',
        'reports/report.xml',
    ],
    
    'installable' : True,
    'application' : True,
    'autoinstall' : False,
}