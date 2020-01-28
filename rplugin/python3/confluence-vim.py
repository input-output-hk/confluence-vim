import neovim
import json
import html2text
import requests

@neovim.plugin
class Main(object):
    def __init__(self, vim):
        self.vim = vim

    @neovim.function('OpenConfluencePage')
    def openConfluencePage(self, args):
        self.vim.command('echo "hello from DoItPython"')
        # This should be okay since requests needs urllib
        try:
            from urllib.parse import urlparse
        except ImportError:
            from urlparse import urlparse

        cb = vim.current.buffer

        conf_path = vim.eval("a:conf_path")

        space_name = urlparse(conf_path).netloc
        article_name = urlparse(conf_path).path.split('/')[1]

        eval_value = int(vim.eval('exists("g:confluence_url")'))
        if not eval_value:
        	print("Confluence url value not set: ".format(eval_value))

        confluence_url = vim.eval("g:confluence_url")
        r = requests.get(confluence_url, params={'spaceKey': space_name, 'title': article_name, 'status': 'current', 'expand': 'body.view,version.number', 'limit': 1}, verify=True)

        resp = json.loads(r.text)['results']
        if len(resp) > 0:
            vim.command("let b:confid = %d" % int(resp[0]['id']))
            vim.command("let b:confv = %d" % int(resp[0]['version']['number']))

            article = resp[0]['body']['view']['value']
            h = html2text.HTML2Text()
            h.body_width = 0
            article_markdown = h.handle(article)

            del cb[:]
            for line in article_markdown.split('\n'):
                cb.append(line.encode('utf8'))
            del cb[0]
        else:
            vim.command("let b:confid = 0")
            vim.command("let b:confv = 0")
            vim.command("echo \"New confluence entry - %s\"" % article_name)
        vim.command("set filetype=mkd.markdown")


    @neovim.function('WriteConfluencePage')
    def writeConfluencePage(self, args):
        try:
            from urllib.parse import urlparse
        except ImportError:
            from urlparse import urlparse

        cb = vim.current.buffer

        conf_path = vim.eval("a:conf_path")

        space_name = urlparse(conf_path).netloc
        article_name = urlparse(conf_path).path.split('/')[1]

        article_id = int(vim.eval("b:confid"))
        article_v = int(vim.eval("b:confv")) + 1
        article_content = markdown.markdown("\n".join(cb))

        eval_value = int(vim.eval('exists("g:confluence_url")'))
        if not eval_value:
        	print("Confluence url value not set: ".format(eval_value))

        confluence_url = vim.eval("g:confluence_url")

        if article_id > 0:
            jj = {"id": str(article_id), "title": article_name, "type": "page", "space": { "key": space_name }, "version": { "number": article_v }, "body": { "storage": { "value": article_content, "representation": "storage" } } }
            #r = requests.put('%s/%d' % (confluence_url, article_id), json=jj, verify=True)
            r = requests.put('%s/%d' % (confluence_url, article_id), data=json.dumps(jj), verify=True, headers={"content-type":"application/json"})
        else:
            jj = {"type": "page", "space": {"key": space_name}, "title": article_name, "body": {"storage": {"value": article_content, "representation": "storage"}}}
            #r = requests.post('%s' % confluence_url, params={'spaceKey': space_name, 'title': article_name}, json=jj, verify=True)
            r = requests.post('%s' % confluence_url, params={'spaceKey': space_name, 'title': article_name}, data=json.dumps(jj), verify=True, headers={"content-type":"application/json"})

        resp = json.loads(r.text)
        vim.command("let b:confid = %d" % int(resp['id']))
        vim.command("let b:confv = %d" % int(resp['version']['number']))
        vim.command("let &modified = 0")
        vim.command("echo \"Confluence entry %s written to space %s.\"" % (article_name, space_name))
