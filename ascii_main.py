import os
import webapp2
import urllib2
from xml.dom import minidom
import jinja2
from google.appengine.ext import db
from google.appengine.api import memcache
import logging

jinja_environment = jinja2.Environment(autoescape=True,
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

IP_URL = "http://api.hostip.info/?ip="
#ip = "4.2.2.2"
#ip = "46.36.198.121"

def get_coords(ip):
	url = IP_URL+ip
	content = None
	try:
		content = urllib2.urlopen(url).read()
	except URLError:
		return
	if content:
		 x = minidom.parseString(content)
    	coords = x.getElementsByTagName("gml:coordinates")
    	if coords and coords[0].childNodes[0].nodeValue:
        	lon, lat = coords[0].childNodes[0].nodeValue.split(',')
        	return db.GeoPt(lat, lon)

GMAPS_URL = "http://maps.googleapis.com/maps/api/staticmap?size=380x263&sensor=false&"

def gmaps_img(points):
    markers = '&'.join('markers=%s,%s' % (p.lat,p.lon) for p in points)
    return GMAPS_URL + markers

    

def top_arts(update = False):
	key = 'top'
	arts = memcache.get(key)
	if arts is None or update:
		logging.error("DB QUERY")
		#retrieve the database art
		arts=db.GqlQuery("SELECT * FROM Art " "ORDER BY created DESC " "LIMIT 10")
		arts = list(arts)
		memcache.set(key,arts)
	return arts





class Art(db.Model):
	title = db.StringProperty(required=True)
	art = db.TextProperty(required=True)
	created=db.DateTimeProperty(auto_now_add=True)
	coords = db.GeoPtProperty()


class Handler(webapp2.RequestHandler):
	def write(self,*a,**kw):
		self.response.out.write(*a,**kw)

	def render_str(self, template, **params):
		t = jinja_environment.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

class MainPage(Handler):
	def render_front(self, title="",art="",error=""):
		arts = top_arts()

		#find which arts have coords
		points = filter(None, (a.coords for a in arts))
		img_url = None
		if points:
			img_url = gmaps_img(points)

		#display the image URL


		self.render("index.html",title=title, art=art,error=error,arts=arts,img_url =img_url)
	
	def get(self):
		#self.write(repr(gmaps_img(get_coords(ip))))
		self.write(repr(self.request.remote_addr))
		self.write(repr(get_coords(self.request.remote_addr)))
		#self.write(repr(get_coords(self.request.remote_addr)))
		self.render_front()
		

	def post(self):
		title = self.request.get('title')
		art = self.request.get('art')

		if title and art:
			a = Art(title=title,art=art)
			#coords = get_coords(ip)
			coords = get_coords(self.request.remote_addr)
			if coords:
				a.coords=coords

			a.put()
			memcache.flush_all()

			self.redirect('/')
			

		else:
			error = "We need both a title and some artwork!"
			self.render_front(title,art,error)	



application = webapp2.WSGIApplication([('/',MainPage)],debug=True)
