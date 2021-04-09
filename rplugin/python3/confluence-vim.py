import neovim
import json
import html2text
import requests
import markdown

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


@neovim.plugin
class Main(object):
    def __init__(self, nvim):
        self.nvim = nvim

    @neovim.autocmd('BufReadCmd', pattern="conf://*", eval='expand("<amatch>")', sync=True)
    def bufread_handler(self, filename):
        self.nvim.command(f"call OpenConfluencePage('{filename}')")
    @neovim.autocmd('BufWriteCmd', pattern="conf://*", eval='expand("<amatch>")', sync=True)
    def bufwrite_handler(self, filename):
        self.nvim.command(f"call WriteConfluencePage('{filename}')")

    def fetchConfluencePage(self, space, article_name):
        params={'spaceKey': space, 'title': article_name, 'status': 'current', 'expand': 'body.view,version', 'limit': 1}
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
            return { 'article': article_markdown, 'version': confVersion, 'id': confId }
        else:
            return { 'article': "", 'version': 0, 'id': 0 }

    @neovim.function('OpenConfluencePage')
    def openConfluencePage(self, args):
        self.user = self.nvim.vars['confluence_user']
        self.apikey = self.nvim.vars['confluence_apikey']
        self.url = self.nvim.vars['confluence_url']
        conf_path = args[0]

        cb = self.nvim.current.buffer

        space_name = urlparse(conf_path).netloc
        article_name = urlparse(conf_path).path.split('/')[1]
        article_name = article_name.replace('\\', '')

        article_data = self.fetchConfluencePage(space_name, article_name)
        article_version = article_data["version"]
        article = article_data["article"]
        article_id = article_data["id"]
        del cb[:]
        if article != "":
            for line in article.split('\n'):
                cb.append(line.encode('utf8'))
                self.nvim.command(f"let b:confluence_id = {article_id}")
                self.nvim.command(f"let b:confluence_version = {article_version}")
                self.nvim.command(f"let b:confluence_article = '{article_name}'")
                self.nvim.command(f"let b:confluence_space = '{space_name}'")
            del cb[0]
        else:
            self.nvim.command("let b:confluence_id = 0")
            self.nvim.command("let b:confluence_version = 0")
            self.nvim.command(f"let b:confluence_article = '{article_name}'")
            self.nvim.command(f"let b:confluence_space = '{space_name}'")
            self.nvim.command("echo \"New confluence entry - %s\"" % article_name)
        self.nvim.command("set filetype=mkd.markdown")

    def updateConfluencePage(self, article_space, article_name, article_id, article_version, article_contents):
        if article_id > 0:
            jj = {"id": str(article_id), "title": article_name, "type": "page", "space": { "key": article_space }, "version": { "number": article_version }, "body": { "storage": { "value": article_contents, "representation": "storage" } } }
            r = requests.put(f"{self.url}/{article_id}", data=json.dumps(jj), verify=True, headers={"content-type":"application/json"}, auth=(self.user, self.apikey) )
        else:
            jj = {"type": "page", "space": {"key": article_space}, "title": article_name, "body": {"storage": {"value": article_contents, "representation": "storage"}}}
            r = requests.post(f"{self.url}", params={'spaceKey': article_space, 'title': article_name}, data=json.dumps(jj), verify=True, headers={"content-type":"application/json"}, auth=(self.user, self.apikey) )
        return r

    @neovim.function('WriteConfluencePage')
    def writeConfluencePage(self, args):
        self.user = self.nvim.vars['confluence_user']
        self.apikey = self.nvim.vars['confluence_apikey']
        self.url = self.nvim.vars['confluence_url']
        cb = self.nvim.current.buffer

        article_id = int(self.nvim.eval("b:confluence_id"))
        article_version = int(self.nvim.eval("b:confluence_version")) + 1
        article_space = str(self.nvim.eval("b:confluence_space"))
        article_name = str(self.nvim.eval("b:confluence_article"))
        article_contents = markdown.markdown("\n".join(cb))
        r = self.updateConfluencePage(article_space, article_name, article_id, article_version, article_contents)

        resp = json.loads(r.text)
        self.nvim.command("let b:confluence_id = %d" % int(resp['id']))
        self.nvim.command("let b:confluence_version = %d" % int(resp['version']['number']))
        self.nvim.command("let &modified = 0")
        self.nvim.command(f"echo \"Confluence entry {article_name} written to space {article_space}.\"")
