{
    'name' : 'Management System',
    'author' : 'apocalypse',
    'summary' : 'Quotation Sales',
    'depends' : ['mail', 'base', 'project', 'sale'],
    'sequence' : -1000,
    'data' :[
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu.xml',
        'views/sales.xml',
        'views/invoice.xml',
        'reports/report.xml',
    ],
    
    'installable' : True,
    'application' : True,
    'autoinstall' : False,
}