# -*- coding: utf-8 -*-
{
    'name': "Secuencias nro factura, nd,nc y nro control por diario",

    'summary': """Secuencias nro factura, nd,nc y nro control por diario""",

    'description': """
       Secuencias nro factura, nd,nc y nro control por diario.
    """,
    'version': '13.0',
    'author': 'INM & LDR Soluciones Tecnológicas y Empresariales C.A',
    'category': 'Tools',
    'website': 'http://soluciones-tecno.com/',

    # any module necessary for this one to work correctly
    'depends': ['base','account','vat_retention','ext_personalizacion_lanta','l10n_ve_fiscal_requirements','l10n_ve_formato_factura_nd_nc','multiple_sucursales','ext_filtros_diarios_fact'],

    # always loaded
    'data': [
        'vista/account_journal_views.xml',
        'vista/company_inherit_views.xml',
        #'formatos/nota_entrega.xml',
        #'formatos/account_move_view.xml',
    	#'security/ir.model.access.csv',
        #'resumen_iva/reporte_view.xml',
        #'resumen_iva/wizard.xml',
        #'resumen_municipal/wizard.xml',
        #'resumen_municipal/reporte_view.xml',
        #'resumen_islr/wizard.xml',
        #'resumen_islr/reporte_view.xml',
    ],
    'application': True,
    'active':False,
    'auto_install': False,
}
