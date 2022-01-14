{
    "name":"Extensión para Reportes de Calle",
    "description":"Permite añadir realizar reportes de promedio de días y días de calle.",
    "author":"Oasis Consultora",
    "depends":['account', 'account_accountant', 'administration_module'],
    "data":[
        'views/views.xml',
        'views/wizards_days.xml',
        'views/wizards_street_days_report.xml',
        'security/security.xml',
        'reports/days_report.xml',
        'reports/street_days_report.xml'

    ]
}