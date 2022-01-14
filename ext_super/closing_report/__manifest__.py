{
    "name":"Reportes de Cierre de Cobranzas",
    "description":"Permite añadir realizar reportes de cierre de cobranzas.",
    "author":"Oasis Consultora",
    "depends":['account', 'account_accountant', ],
    "data":[
        'views/wizards_closing_report.xml',
        'views/account_payment_views.xml',
        'security/security.xml',
        'reports/closing_report.xml'
    ]
}