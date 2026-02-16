from ddgs import DDGS

with DDGS() as ddgs:
    results = [r['body'] for r in ddgs.text('Narendra Modi early life biography')]

with open('modi_bio.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))