import neovim
import json
import html2text
import requests

@neovim.plugin
class Main(object):
    def __init__(self, nvim):
        self.nvim = nvim

    @neovim.autocmd('BufReadCmd', pattern="conf://*", eval='expand("<amatch>")', sync=True)
    def bufread_handler(self, filename):
        self.nvim.command(f"call OpenConfluencePage({filename})")

    def fetchConfluencePage(self, space, article_name):
        params={'spaceKey': space, 'title': article_name, 'status': 'current', 'expand': 'body.view.version.number', 'limit': 1}
        r = requests.get(self.url, params=params , verify=True, auth=(self.user, self.apikey))
        resp = json.loads(r.text)['results']
        if len(resp) > 0:
            confId = int(resp[0]['id'])
            if 'version' in resp[0]:
                confVersion = int(resp[0]['version']['number'])
            else:
                confVersion = 0
            article = resp[0]['body']['view']['value']
            h = html2text.HTML2Text()
            h.body_width = 0
            article_markdown = h.handle(article)
            return { 'article': article_markdown, 'version': confVersion }
        else:
            return { 'article': "", 'version': 0 }


    @neovim.function('OpenConfluencePage')
    def openConfluencePage(self, args):
        self.user = self.nvim.vars['confluence_user']
        self.apikey = self.nvim.vars['confluence_apikey']
        self.url = self.nvim.vars['confluence_url']
        conf_path = args[0]

        # This should be okay since requests needs urllib
        try:
            from urllib.parse import urlparse
        except ImportError:
            from urlparse import urlparse

        cb = self.nvim.current.buffer

        space_name = urlparse(conf_path).netloc
        article_name = urlparse(conf_path).path.split('/')[1]

        article_data = self.fetchConfluencePage(space_name, article_name)
        article_version = article_data["version"]
        article = article_data["article"]
        del cb[:]
        if article != "":
            for line in article.split('\n'):
                cb.append(line.encode('utf8'))
                self.nvim.command(f"let b:confv = {article_version}")
            del cb[0]
        else:
            self.nvim.command("let b:confid = 0")
            self.nvim.command("let b:confv = 0")
            self.nvim.command("echo \"New confluence entry - %s\"" % article_name)
        self.nvim.command("set filetype=mkd.markdown")

    @neovim.function('WriteConfluencePage')
    def writeConfluencePage(self, args):
        try:
            from urllib.parse import urlparse
        except ImportError:
            from urlparse import urlparse

        cb = vim.current.buffer

        conf_path = args[0]

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
