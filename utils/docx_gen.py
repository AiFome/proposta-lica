import io, zipfile

def xe(s):
    return str(s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace("'",'&apos;')

def par(text, bold=False, sz=20, jc='left', color=None, after=80):
    b = '<w:b/><w:bCs/>' if bold else ''
    c = f'<w:color w:val="{color}"/>' if color else ''
    return (f'<w:p><w:pPr><w:spacing w:after="{after}"/><w:jc w:val="{jc}"/>'
            f'<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>{b}<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>{c}</w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>{b}<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>{c}</w:rPr>'
            f'<w:t xml:space="preserve">{xe(text)}</w:t></w:r></w:p>')

def cel(text, w=2000, bold=False, sz=16, jc='left', shade=None, tc=None):
    b = '<w:b/><w:bCs/>' if bold else ''
    sh = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ''
    tcc = f'<w:color w:val="{tc}"/>' if tc else ''
    bdr = ('<w:tcBorders>'
           '<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           '<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           '<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           '</w:tcBorders>')
    return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{bdr}{sh}<w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p><w:pPr><w:jc w:val="{jc}"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>{b}'
            f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>{tcc}</w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>{b}'
            f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>{tcc}</w:rPr>'
            f'<w:t xml:space="preserve">{xe(text)}</w:t></w:r></w:p></w:tc>')

def row(*cells):
    return f'<w:tr><w:trPr><w:trHeight w:val="400" w:hRule="atLeast"/></w:trPr>{"".join(cells)}</w:tr>'

def safe(v, default=''):
    """Garante que o valor nunca é None."""
    if v is None: return default
    return str(v).strip()

def gerar_docx(empresa, edital, itens, modelo=None):
    # Garantir que nenhum argumento é None
    empresa = empresa or {}
    edital  = edital  or {}
    itens   = itens   or []
    modelo  = modelo  or {}

    W = {'num':700,'desc':5500,'qtd':700,'unid':900,'produto':2900,'vunit':1900,'vtotal':1940}
    TW = sum(W.values())

    # Modelo de texto — com fallbacks seguros
    validade = safe(modelo.get('validade'), '60 (SESSENTA) DIAS, A CONTAR DA DATA DA APRESENTACAO.')
    prazo    = safe(modelo.get('prazo'),    'CONFORME EDITAL.')
    local_e  = safe(modelo.get('local'),   'CONFORME EDITAL.')
    decl_txt = safe(modelo.get('decl'),    '')
    obs_txt  = safe(modelo.get('obs'),     '')

    if decl_txt:
        decls = [d.strip() for d in decl_txt.split('\n') if d.strip()]
    else:
        decls = []

    if not decls:
        decls = [
            'Declaramos conhecer a legislacao de referencia desta licitacao e que os produtos serao fornecidos de acordo com as condicoes estabelecidas neste Edital.',
            'Declaro que nos precos propostos encontram-se incluidos todos os valores de tributos, encargos sociais, frete ate o destino e quaisquer outros onus.',
            'Declaramos estar de acordo com todas as normas deste edital e seus anexos.',
            'Declaramos, sob as penas da lei, que esta proposta atende a todos os requisitos constantes do edital.',
        ]

    # Dados da empresa — com fallbacks seguros
    razao = safe(empresa.get('razao_social') or empresa.get('razao'))
    cnpj  = safe(empresa.get('cnpj'))
    ie    = safe(empresa.get('ie'))
    tel   = safe(empresa.get('telefone') or empresa.get('tel'))
    email = safe(empresa.get('email_comercial') or empresa.get('email'))
    end   = safe(empresa.get('endereco'))
    banco = safe(empresa.get('banco'))
    rep   = safe(empresa.get('representante') or empresa.get('rep'))
    cpfrg = safe(empresa.get('cpfrg'))

    # Dados do edital — com fallbacks seguros
    pref      = safe(edital.get('prefeitura')).upper()
    pregao    = safe(edital.get('pregao'))
    processo  = safe(edital.get('processo'))
    plataforma= safe(edital.get('plataforma'))
    objeto    = safe(edital.get('objeto'))

    cab = ''.join([
        par(razao, bold=True, sz=22, jc='center', after=60),
        par(f'CNPJ: {cnpj}  |  INSCRICAO ESTADUAL: {ie}', bold=True, sz=20, jc='center', after=40),
        par(f'TELEFONE: {tel}   |   E-MAIL: {email}', sz=20, jc='center', after=40),
        par(f'CONTA: {banco}', sz=20, jc='center', after=40),
        par(f'ENDERECO: {end}', sz=20, jc='center', after=40),
        par(f'RESPONSAVEL: {rep}   |   CPF/RG: {cpfrg}', sz=20, jc='center', after=80),
        par(f'PREFEITURA MUNICIPAL DE {pref}', bold=True, sz=20, after=50),
        par(f'PLATAFORMA: {plataforma}', bold=True, sz=20, after=100),
    ])

    tit = ''.join([
        par('PROPOSTA COMERCIAL', bold=True, sz=26, jc='center', after=80),
        par(f'PREGAO ELETRONICO N {pregao}', bold=True, sz=22, jc='center', after=60),
        par(f'PROCESSO LICITATORIO N {processo}', bold=True, sz=22, jc='center', after=100),
        par('A', sz=20, after=40),
        par(f'PREFEITURA MUNICIPAL DE {pref}', bold=True, sz=20, after=100),
        par(f'Objeto: {objeto}', sz=20, after=100),
    ])

    hdr = row(
        cel('ITEM',         w=W['num'],     bold=True, sz=17, jc='center', shade='1A5276', tc='FFFFFF'),
        cel('DESCRICAO',    w=W['desc'],    bold=True, sz=17, jc='center', shade='1A5276', tc='FFFFFF'),
        cel('QTD',          w=W['qtd'],     bold=True, sz=17, jc='center', shade='1A5276', tc='FFFFFF'),
        cel('UNIDADE',      w=W['unid'],    bold=True, sz=17, jc='center', shade='1A5276', tc='FFFFFF'),
        cel('PRODUTO',      w=W['produto'], bold=True, sz=17, jc='center', shade='1A5276', tc='FFFFFF'),
        cel('VL. UNITARIO', w=W['vunit'],   bold=True, sz=17, jc='center', shade='1A5276', tc='FFFFFF'),
        cel('VL. TOTAL',    w=W['vtotal'],  bold=True, sz=17, jc='center', shade='1A5276', tc='FFFFFF'),
    )

    rows_i = ''
    for it in itens:
        p = it.get('produto') or {}
        # Garantir que os campos do produto nunca são None
        nome_prod = safe(p.get('nome'))
        fab_prod  = safe(p.get('fabricante'))
        gram_prod = safe(p.get('gramatura'))
        partes = [x for x in [nome_prod, fab_prod, gram_prod] if x]
        nome_completo = ' / '.join(partes)

        rows_i += row(
            cel(safe(it.get('num')),                             w=W['num'],     jc='center', sz=15),
            cel(safe(it.get('desc')),                            w=W['desc'],    jc='both',   sz=14),
            cel(safe(it.get('qtd')),                             w=W['qtd'],     jc='center', sz=15),
            cel(safe(it.get('unidNorm') or it.get('unid')),     w=W['unid'],    jc='center', sz=15),
            cel(nome_completo,                                   w=W['produto'], jc='center', sz=15),
            cel('R$ ',                                           w=W['vunit'],   jc='center', sz=15),
            cel('R$ ',                                           w=W['vtotal'],  jc='center', sz=15),
        )

    tot = row(
        cel('', w=W['num'],  shade='F2F2F2'),
        cel('', w=W['desc'], shade='F2F2F2'),
        cel('', w=W['qtd'],  shade='F2F2F2'),
        cel('', w=W['unid'], shade='F2F2F2'),
        cel('VALOR TOTAL', w=W['produto'], bold=True, sz=17, jc='center', shade='F2F2F2'),
        cel('', w=W['vunit'], shade='F2F2F2'),
        cel('R$ ', w=W['vtotal'], bold=True, sz=17, jc='center', shade='F2F2F2'),
    )

    gc = ''.join(f'<w:gridCol w:w="{v}"/>' for v in W.values())
    tbl = (f'<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="{TW}" w:type="dxa"/><w:jc w:val="center"/>'
           f'<w:tblBorders>'
           f'<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           f'<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           f'<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           f'</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr>'
           f'<w:tblGrid>{gc}</w:tblGrid>{hdr}{rows_i}{tot}</w:tbl>')

    # Cidade a partir do endereço
    if '/' in end:
        cidade = end.split('/')[-1].strip()
    elif ',' in end:
        cidade = end.split(',')[-1].strip()
    else:
        cidade = end

    rod = ''.join([
        par('', sz=20, after=100),
        par('VALOR TOTAL DA PROPOSTA: R$ ___________', bold=True, sz=20, after=100),
        par(f'PRAZO DE VALIDADE DA PROPOSTA: {validade}', sz=20, after=70),
        par(f'PRAZO DE ENTREGA: {prazo}', sz=20, after=70),
        par(f'LOCAL DE ENTREGA: {local_e}', sz=20, after=100),
        *[par(d, sz=20, after=70) for d in decls],
        *([par(obs_txt, sz=20, after=70)] if obs_txt else []),
        par(f'{cidade}, _____ de _________________ de 2026.', sz=20, jc='right', after=360),
        par('________________________________________', sz=20, jc='center', after=50),
        par(razao, bold=True, sz=20, jc='center', after=50),
        par(f'CNPJ: {cnpj}', sz=20, jc='center', after=50),
        par(f'{rep} - CPF/RG: {cpfrg}', sz=20, jc='center', after=50),
        par(f'ENDERECO: {end}', sz=20, jc='center', after=50),
    ])

    ns = ('xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
          'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"')
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document {ns}><w:body>'
           f'<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
           f'<w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720"/></w:sectPr>'
           f'{cab}{tit}{tbl}{rod}</w:body></w:document>')

    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
              '<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:rPrDefault></w:docDefaults>'
              '<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/>'
              '<w:tblPr><w:tblBorders>'
              '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
              '<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
              '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
              '<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
              '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
              '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
              '</w:tblBorders></w:tblPr></w:style></w:styles>')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
            '</Types>')
        zf.writestr('_rels/.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
        zf.writestr('word/_rels/document.xml.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
            '</Relationships>')
        zf.writestr('word/settings.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:defaultTabStop w:val="720"/></w:settings>')
        zf.writestr('word/styles.xml', styles)
        zf.writestr('word/document.xml', doc)
    return buf.getvalue()
