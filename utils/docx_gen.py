import io, zipfile

def xe(s):
    return str(s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace("'",'&apos;')

def safe(v, default=''):
    if v is None: return default
    return str(v).strip()

def par(text, bold=False, sz=20, jc='left', color=None, after=80, before=0):
    b = '<w:b/><w:bCs/>' if bold else ''
    c = f'<w:color w:val="{color}"/>' if color else ''
    spc = f'<w:spacing w:before="{before}" w:after="{after}"/>'
    return (f'<w:p><w:pPr>{spc}<w:jc w:val="{jc}"/>'
            f'<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>{b}<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>{c}</w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>{b}<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>{c}</w:rPr>'
            f'<w:t xml:space="preserve">{xe(text)}</w:t></w:r></w:p>')

def cel(text, w=2000, bold=False, sz=16, jc='left', shade=None, tc=None, valign='center'):
    b = '<w:b/><w:bCs/>' if bold else ''
    sh = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ''
    tcc = f'<w:color w:val="{tc}"/>' if tc else ''
    bdr = ('<w:tcBorders>'
           '<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           '<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           '<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
           '</w:tcBorders>')
    return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{bdr}{sh}<w:vAlign w:val="{valign}"/></w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:after="40"/><w:jc w:val="{jc}"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>{b}'
            f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>{tcc}</w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>{b}'
            f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>{tcc}</w:rPr>'
            f'<w:t xml:space="preserve">{xe(text)}</w:t></w:r></w:p></w:tc>')

def row(*cells, altura=400):
    return f'<w:tr><w:trPr><w:trHeight w:val="{altura}" w:hRule="atLeast"/></w:trPr>{"".join(cells)}</w:tr>'

def hline():
    """Linha horizontal decorativa."""
    return ('<w:p><w:pPr><w:spacing w:after="0"/><w:pBdr>'
            '<w:bottom w:val="single" w:sz="6" w:space="1" w:color="1A5276"/>'
            '</w:pBdr></w:pPr></w:p>')

def _build_docx(doc_xml, styles_xml):
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
        zf.writestr('word/styles.xml', styles_xml)
        zf.writestr('word/document.xml', doc_xml)
    return buf.getvalue()

def _styles():
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
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

def _rodape_texto(empresa, edital, modelo):
    razao = safe(empresa.get('razao_social') or empresa.get('razao'))
    cnpj  = safe(empresa.get('cnpj'))
    rep   = safe(empresa.get('representante') or empresa.get('rep'))
    cpfrg = safe(empresa.get('cpfrg'))
    end   = safe(empresa.get('endereco'))
    validade = safe(modelo.get('validade'), '60 (SESSENTA) DIAS, A CONTAR DA DATA DA APRESENTACAO.')
    prazo    = safe(modelo.get('prazo'),    'CONFORME EDITAL.')
    local_e  = safe(modelo.get('local'),   'CONFORME EDITAL.')
    decl_txt = safe(modelo.get('decl'))
    obs_txt  = safe(modelo.get('obs'))
    decls = [d.strip() for d in decl_txt.split('\n') if d.strip()] if decl_txt else [
        'Declaramos conhecer a legislacao de referencia desta licitacao e que os produtos serao fornecidos conforme as condicoes estabelecidas neste Edital.',
        'Declaro que nos precos propostos estao incluidos tributos, encargos sociais, frete e quaisquer outros onus.',
        'Declaramos estar de acordo com todas as normas deste edital e seus anexos.',
        'Declaramos, sob as penas da lei, que esta proposta atende a todos os requisitos do edital.',
    ]
    if '/' in end: cidade = end.split('/')[-1].strip()
    elif ',' in end: cidade = end.split(',')[-1].strip()
    else: cidade = end
    return ''.join([
        par('', sz=20, after=80),
        par('VALOR TOTAL DA PROPOSTA: R$ ___________', bold=True, sz=20, after=80),
        par(f'PRAZO DE VALIDADE: {validade}', sz=19, after=60),
        par(f'PRAZO DE ENTREGA: {prazo}', sz=19, after=60),
        par(f'LOCAL DE ENTREGA: {local_e}', sz=19, after=80),
        *[par(d, sz=19, after=60) for d in decls],
        *([par(obs_txt, sz=19, after=60)] if obs_txt else []),
        par(f'{cidade}, _____ de _________________ de 2026.', sz=20, jc='right', after=300),
        par('________________________________________', sz=20, jc='center', after=40),
        par(razao, bold=True, sz=20, jc='center', after=40),
        par(f'CNPJ: {cnpj}', sz=20, jc='center', after=40),
        par(f'{rep} - CPF/RG: {cpfrg}', sz=20, jc='center', after=40),
        par(f'ENDERECO: {end}', sz=20, jc='center', after=40),
    ])

def _tabela_itens(itens):
    W = {'num':700,'desc':5500,'qtd':700,'unid':900,'produto':2900,'vunit':1900,'vtotal':1940}
    TW = sum(W.values())
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
        partes = [x for x in [safe(p.get('nome')), safe(p.get('fabricante')), safe(p.get('gramatura'))] if x]
        rows_i += row(
            cel(safe(it.get('num')),                           w=W['num'],     jc='center', sz=15),
            cel(safe(it.get('desc')),                          w=W['desc'],    jc='both',   sz=14),
            cel(safe(it.get('qtd')),                           w=W['qtd'],     jc='center', sz=15),
            cel(safe(it.get('unidNorm') or it.get('unid')),   w=W['unid'],    jc='center', sz=15),
            cel(' / '.join(partes),                            w=W['produto'], jc='center', sz=15),
            cel('R$ ',                                         w=W['vunit'],   jc='center', sz=15),
            cel('R$ ',                                         w=W['vtotal'],  jc='center', sz=15),
        )
    tot = row(
        cel('', w=W['num'],  shade='F2F2F2'), cel('', w=W['desc'], shade='F2F2F2'),
        cel('', w=W['qtd'],  shade='F2F2F2'), cel('', w=W['unid'], shade='F2F2F2'),
        cel('VALOR TOTAL', w=W['produto'], bold=True, sz=17, jc='center', shade='F2F2F2'),
        cel('', w=W['vunit'], shade='F2F2F2'),
        cel('R$ ', w=W['vtotal'], bold=True, sz=17, jc='center', shade='F2F2F2'),
    )
    gc = ''.join(f'<w:gridCol w:w="{v}"/>' for v in W.values())
    return (f'<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="{TW}" w:type="dxa"/>'
            f'<w:jc w:val="center"/><w:tblBorders>'
            f'<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            f'</w:tblBorders><w:tblLayout w:type="fixed"/></w:tblPr>'
            f'<w:tblGrid>{gc}</w:tblGrid>{hdr}{rows_i}{tot}</w:tbl>')

# ════════════════════════════════════════════════════════
# MODELO 1 — PADRÃO (cabeçalho empresa + tabela + rodapé)
# ════════════════════════════════════════════════════════
def modelo_padrao(empresa, edital, itens, modelo):
    razao = safe(empresa.get('razao_social') or empresa.get('razao'))
    cnpj  = safe(empresa.get('cnpj'))
    ie    = safe(empresa.get('ie'))
    tel   = safe(empresa.get('telefone') or empresa.get('tel'))
    email = safe(empresa.get('email_comercial') or empresa.get('email'))
    end   = safe(empresa.get('endereco'))
    banco = safe(empresa.get('banco'))
    rep   = safe(empresa.get('representante') or empresa.get('rep'))
    cpfrg = safe(empresa.get('cpfrg'))
    pref  = safe(edital.get('prefeitura')).upper()

    # Cabeçalho da empresa dentro de tabela (mais profissional)
    W_cab = {'logo': 2000, 'info': 8640}
    cab_tbl = (f'<w:tbl><w:tblPr>'
               f'<w:tblW w:w="{sum(W_cab.values())}" w:type="dxa"/>'
               f'<w:tblBorders>'
               f'<w:top w:val="single" w:sz="8" w:space="0" w:color="1A5276"/>'
               f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="1A5276"/>'
               f'<w:insideH w:val="none"/><w:insideV w:val="none"/>'
               f'<w:left w:val="none"/><w:right w:val="none"/>'
               f'</w:tblBorders>'
               f'<w:tblLayout w:type="fixed"/></w:tblPr>'
               f'<w:tblGrid><w:gridCol w:w="{W_cab["logo"]}"/><w:gridCol w:w="{W_cab["info"]}"/></w:tblGrid>'
               f'<w:tr><w:trPr><w:trHeight w:val="1200" w:hRule="atLeast"/></w:trPr>'
               # Coluna esquerda — ícone/sigla
               f'<w:tc><w:tcPr><w:tcW w:w="{W_cab["logo"]}" w:type="dxa"/>'
               f'<w:shd w:val="clear" w:color="auto" w:fill="1A5276"/>'
               f'<w:vAlign w:val="center"/></w:tcPr>'
               f'<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="0"/></w:pPr>'
               f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:b/><w:bCs/>'
               f'<w:sz w:val="48"/><w:szCs w:val="48"/><w:color w:val="FFFFFF"/></w:rPr>'
               f'<w:t>{xe(razao[:2].upper() if razao else "PL")}</w:t></w:r></w:p></w:tc>'
               # Coluna direita — dados da empresa
               f'<w:tc><w:tcPr><w:tcW w:w="{W_cab["info"]}" w:type="dxa"/>'
               f'<w:shd w:val="clear" w:color="auto" w:fill="EAF0FB"/>'
               f'<w:vAlign w:val="center"/></w:tcPr>'
               f'<w:p><w:pPr><w:spacing w:after="20"/><w:ind w:left="120"/></w:pPr>'
               f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:b/><w:bCs/>'
               f'<w:sz w:val="28"/><w:szCs w:val="28"/><w:color w:val="1A5276"/></w:rPr>'
               f'<w:t>{xe(razao)}</w:t></w:r></w:p>'
               f'<w:p><w:pPr><w:spacing w:after="0"/><w:ind w:left="120"/></w:pPr>'
               f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
               f'<w:sz w:val="18"/><w:szCs w:val="18"/><w:color w:val="444444"/></w:rPr>'
               f'<w:t xml:space="preserve">CNPJ: {xe(cnpj)}  |  IE: {xe(ie)}  |  Tel: {xe(tel)}</w:t></w:r></w:p>'
               f'<w:p><w:pPr><w:spacing w:after="0"/><w:ind w:left="120"/></w:pPr>'
               f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
               f'<w:sz w:val="18"/><w:szCs w:val="18"/><w:color w:val="444444"/></w:rPr>'
               f'<w:t xml:space="preserve">Email: {xe(email)}  |  {xe(end)}</w:t></w:r></w:p>'
               f'<w:p><w:pPr><w:spacing w:after="0"/><w:ind w:left="120"/></w:pPr>'
               f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
               f'<w:sz w:val="18"/><w:szCs w:val="18"/><w:color w:val="444444"/></w:rPr>'
               f'<w:t xml:space="preserve">Banco/Conta: {xe(banco)}  |  Resp: {xe(rep)} - {xe(cpfrg)}</w:t></w:r></w:p>'
               f'</w:tc></w:tr></w:tbl>')

    tit = ''.join([
        par('', sz=20, after=60),
        par('PROPOSTA COMERCIAL', bold=True, sz=26, jc='center', after=40, color='1A5276'),
        par(f'Pregao Eletronico N {safe(edital.get("pregao"))}  |  Processo N {safe(edital.get("processo"))}', bold=True, sz=20, jc='center', after=40),
        par(f'Prefeitura Municipal de {pref}', sz=19, jc='center', after=20),
        par(f'Plataforma: {safe(edital.get("plataforma"))}', sz=18, jc='center', after=40),
        par(f'Objeto: {safe(edital.get("objeto"))}', sz=18, jc='center', after=80),
        hline(),
        par('', sz=16, after=60),
    ])

    tbl  = _tabela_itens(itens)
    rod  = _rodape_texto(empresa, edital, modelo)
    ns   = ('xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"')
    doc  = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document {ns}><w:body>'
            f'<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
            f'<w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720"/></w:sectPr>'
            f'{cab_tbl}{tit}{tbl}{rod}</w:body></w:document>')
    return _build_docx(doc, _styles())


# ════════════════════════════════════════════════════════
# MODELO 2 — FORMAL (cabeçalho centralizado clássico)
# ════════════════════════════════════════════════════════
def modelo_formal(empresa, edital, itens, modelo):
    razao = safe(empresa.get('razao_social') or empresa.get('razao'))
    cnpj  = safe(empresa.get('cnpj'))
    ie    = safe(empresa.get('ie'))
    tel   = safe(empresa.get('telefone') or empresa.get('tel'))
    email = safe(empresa.get('email_comercial') or empresa.get('email'))
    end   = safe(empresa.get('endereco'))
    banco = safe(empresa.get('banco'))
    rep   = safe(empresa.get('representante') or empresa.get('rep'))
    cpfrg = safe(empresa.get('cpfrg'))
    pref  = safe(edital.get('prefeitura')).upper()

    cab = ''.join([
        par('━' * 80, sz=14, jc='center', after=20, color='1A5276'),
        par(razao, bold=True, sz=28, jc='center', after=30, color='1A5276'),
        par(f'CNPJ: {cnpj}   |   IE: {ie}   |   Tel: {tel}', bold=True, sz=18, jc='center', after=20),
        par(f'Email: {email}   |   Conta: {banco}', sz=17, jc='center', after=20),
        par(f'Endereco: {end}', sz=17, jc='center', after=20),
        par(f'Responsavel: {rep}   |   CPF/RG: {cpfrg}', sz=17, jc='center', after=20),
        par('━' * 80, sz=14, jc='center', after=60, color='1A5276'),
    ])
    tit = ''.join([
        par('PROPOSTA COMERCIAL', bold=True, sz=28, jc='center', after=30),
        par(f'PREGAO ELETRONICO N {safe(edital.get("pregao"))}', bold=True, sz=22, jc='center', after=20),
        par(f'PROCESSO LICITATORIO N {safe(edital.get("processo"))}', bold=True, sz=20, jc='center', after=40),
        par(f'PREFEITURA MUNICIPAL DE {pref}', bold=True, sz=20, jc='center', after=30),
        par(f'Plataforma: {safe(edital.get("plataforma"))}', sz=18, jc='center', after=20),
        par(f'Objeto: {safe(edital.get("objeto"))}', sz=18, jc='center', after=80),
    ])
    tbl = _tabela_itens(itens)
    rod = _rodape_texto(empresa, edital, modelo)
    ns  = ('xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
           'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"')
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document {ns}><w:body>'
           f'<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
           f'<w:pgMar w:top="800" w:right="720" w:bottom="800" w:left="720"/></w:sectPr>'
           f'{cab}{tit}{tbl}{rod}</w:body></w:document>')
    return _build_docx(doc, _styles())


# ════════════════════════════════════════════════════════
# MODELO 3 — MINIMALISTA (só a tabela com header simples)
# ════════════════════════════════════════════════════════
def modelo_minimalista(empresa, edital, itens, modelo):
    razao = safe(empresa.get('razao_social') or empresa.get('razao'))
    cnpj  = safe(empresa.get('cnpj'))
    pref  = safe(edital.get('prefeitura')).upper()

    cab = ''.join([
        par(razao, bold=True, sz=24, jc='left', after=10, color='1A5276'),
        par(f'CNPJ: {cnpj}   |   {safe(empresa.get("endereco"))}', sz=17, after=10),
        par(f'Tel: {safe(empresa.get("telefone") or empresa.get("tel"))}   |   {safe(empresa.get("email_comercial") or empresa.get("email"))}', sz=17, after=40),
        hline(),
        par(f'PROPOSTA COMERCIAL — PREGAO N {safe(edital.get("pregao"))} — {pref}', bold=True, sz=20, jc='center', after=10),
        par(f'Plataforma: {safe(edital.get("plataforma"))}   |   Objeto: {safe(edital.get("objeto"))[:100]}', sz=16, jc='center', after=40),
    ])
    tbl = _tabela_itens(itens)
    rod = _rodape_texto(empresa, edital, modelo)
    ns  = ('xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
           'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"')
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document {ns}><w:body>'
           f'<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
           f'<w:pgMar w:top="600" w:right="600" w:bottom="600" w:left="600"/></w:sectPr>'
           f'{cab}{tbl}{rod}</w:body></w:document>')
    return _build_docx(doc, _styles())


# ════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════
MODELOS = {
    'padrao':      ('Padrão', 'Cabeçalho colorido com dados da empresa em destaque', modelo_padrao),
    'formal':      ('Formal', 'Cabeçalho centralizado clássico para licitações formais', modelo_formal),
    'minimalista': ('Minimalista', 'Layout compacto, ideal para editais com muitos itens', modelo_minimalista),
}

def gerar_docx(empresa, edital, itens, modelo=None, estilo='padrao'):
    empresa = empresa or {}
    edital  = edital  or {}
    itens   = itens   or []
    modelo  = modelo  or {}
    estilo  = estilo  or 'padrao'

    fn = MODELOS.get(estilo, MODELOS['padrao'])[2]
    return fn(empresa, edital, itens, modelo)
