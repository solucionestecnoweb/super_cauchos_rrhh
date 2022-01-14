{
    'name': "Comprobante mayorizado",
    'description':"Emisión del comprobante mayorizado",
    'depends':['l10n_ve_libro_diario'],
    'data':[
        'report/proof_receipt_report.xml',
        'views/wizard_proof_receipt.xml'  
    ]
}