from flask import Flask, render_template, request, Response, url_for
from flask_httpauth import HTTPBasicAuth
from datetime import datetime
import re, pickle, os.path, time, hashlib, sys
import mysql.connector as mariadb

sys.path.append('../')
from config import *

reload(sys)
sys.setdefaultencoding('utf-8')

app = Flask(__name__)
auth = HTTPBasicAuth()
out_file = None

def demo_data():
	demo_cache = HOME_DIR + "demo_data.p"
	if os.path.isfile(demo_cache):
		return pickle.load(open(demo_cache, "rb" ))
	else:
		return None

def top_tags():
	top_cache = HOME_DIR + "top_tags.p"
	if os.path.isfile(top_cache):
		return pickle.load(open(top_cache, "rb" ))[:10]
	else:
		return []

@app.route('/grebe/')
def grebe():
	stats_cache = HOME_DIR + "stats.p"
	if os.path.isfile(stats_cache):
		counts = pickle.load(open(stats_cache, "rb" ))
		unistat = str(counts[0])[:-6]
	else:
		counts = 0
		unistat = 0

	return render_template('grebe/index.html',active='index',counts=counts,unistat=unistat,provinces=CANADA_PROVINCES)

@app.route('/grebe/about/')
def about():
	return render_template('grebe/about.html',active='about')

@app.route('/grebe/api/demo/')
def api_demo():
	demo_tweets = demo_data()
	return render_template('grebe/demo/api.html',active='api',tweets=demo_tweets)

@app.route('/grebe/api/demo/json/')
def json_demo():
	demo_tweets = demo_data()
	fields = 'tweet, longitude, latitude, created_at, place_name'

	out = '[\n'
	for tweet in demo_tweets:
		i = 0
		out += "\t{\n"
		for field in fields.split(','):
			text = str(tweet[i])
			out += '\t\t"' + field.strip() + '":"' + text + '",\n'
			i += 1
		out = out[:-2] + "\n\t},\n"
	out = out[:-2]+'\n'

	if len(out.strip()) == 0:
		return ""
	else:
		out += ']'
		return out

@app.route('/grebe/timemap/demo/')
def timemap_demo():
	demo_tweets = demo_data()
	if request.args.get('hash'):
		filter_word = '#'+request.args.get('hash').replace('#','').strip()

		sel_tweets = []
		for tweet in demo_tweets:
			txt = tweet[0].encode('punycode')
			if re.search(filter_word, txt, re.IGNORECASE):
				sel_tweets.append(tweet)
			else:
				continue
	else:
		sel_tweets = demo_tweets
		filter_word = ""

	tw = top_tags()
	return render_template('grebe/demo/timemap.html',active='timemap',tweets=sel_tweets,top_words=tw,selw=filter_word,custom=request.args.get('custom'))

@app.route('/grebe/graph/demo/')
def graph_demo():
	demo_tweets = demo_data()
	if demo_tweets:
		dates = [d[3] for d in demo_tweets]
	else:
		dates = []
	unique_dates = list(set(dates))

	if request.args.get('hash'):
		filter_word = '#'+request.args.get('hash').replace('#','').strip()

		sel_tweets = []
		for tweet in demo_tweets:
			txt = tweet[0].encode('punycode')
			if re.search(filter_word, txt, re.IGNORECASE):
				sel_tweets.append(tweet)
			else:
				continue
	else:
		sel_tweets = demo_tweets
		filter_word = ""

	sel_prov = ''
	if request.args.get('province'):
		province = request.args.get('province').strip()
		if province in CANADA_PROVINCES:
			sel_prov = province
			old_sel_tweets = sel_tweets
			sel_tweets = []
			for tweet in old_sel_tweets:
				prov = tweet[4]
				if re.search(province, prov, re.IGNORECASE):
					sel_tweets.append(tweet)
				else:
					continue

	if request.args.get('hash'):
		tw = ['#'+request.args.get('hash').replace('#','').strip()]
		print tw
	else:
		tw = top_tags()

	header = 'Date,'
	for k in tw:
		header += k + ','
	header = header[:-1]
	
	stats = ''
	for date in unique_dates:
		date = str(date).split()[0]
		stats += date + ','
		for k in tw:
			count = 0
			for tweet in sel_tweets:
				cd = str(tweet[3]).split()[0]
				if date != cd: continue
				txt = tweet[0].encode('punycode')
				if re.search(k, txt, re.IGNORECASE):
					count += 1
			stats += str(count) + ','
		stats = stats[:-1] + '\\n'

	tw = top_tags()
	
	return render_template('grebe/demo/graph.html',active='graph',stats=stats,header=header,top_words=tw,selw=filter_word,sel_prov=sel_prov,provinces=CANADA_PROVINCES)

@app.route("/grebe/api/", methods=['GET'])
@auth.login_required
def api():
	try:
		start = request.args.get('start')
		end = request.args.get('end')

		start = datetime.strptime(start, '%d-%m-%Y')
		end =  datetime.strptime(end, '%d-%m-%Y')

		if end < start:
			raise Exception('The end date is before the start date')

		delta = end-start
		if delta.days > MAX_DATE_RANGE:
			raise Exception('The API supports a maximum range of ' + str(MAX_DATE_RANGE) + ' days')

		if request.args.get('fields'):
			fields = request.args.get('fields')
		else:
			fields = 'tweet, longitude, latitude, created_at, place_name'
		
		legal_fields = 'id, tweet, longitude, latitude, created_at, collected_at, lang, place_name, country_code, user_ppid'

		for field in fields.split(','):
			if field not in legal_fields:
				raise Exception('Some specified fields are not supported')
		
		if 'user_ppid' in fields:
			fields = fields.replace('user_ppid', "user_id")
		
		strict_filter = "longitude Is Not Null AND latitude Is Not Null AND "
		qry = "SELECT " + fields + " FROM tweets WHERE " + strict_filter + " created_at >= '" + str(start) + "' AND created_at <= '" + str(end) + "'"
		
		if request.args.get('province'):
			province = request.args.get('province')
			if province in CANADA_PROVINCES:
				qry += " AND (place_name Like '%" + province + "')"
			else:
				raise Exception('The Province code is invalid')
		else:
			raise Exception('The Province filter is required')

		if request.args.get('keywords'):
			keywords = request.args.get('keywords').lower().replace(' ','+')
			st = "tweet Like '%"
			keywords = keywords.replace('+', "%' AND " + st)
			keywords = keywords.replace('|', "%' OR " + st)
			qry += " AND (" + st + keywords + "%')"
		else:
			keywords = ""

		signature = HOME_DIR+hashlib.sha1(str(start)+str(end)+province+keywords+fields).hexdigest()+'.p'
		if os.path.isfile(signature):
			out = pickle.load(open(signature, "rb" ))
		else:
			mariadb_connection = mariadb.connect(user=DB_USER, password=DB_PWD, database=DB_NAME)
			cursor = mariadb_connection.cursor()
			cursor.execute(qry)
			tweets = list(cursor)

			out = '[\n'
			for tweet in tweets:
				i = 0
				out += "\t{\n"
				for field in fields.split(','):
					if field == 'user_id':
						field = 'user_ppid'
						text = hashlib.sha512(tweet[i]+PPID_SALT).hexdigest()
					else:
						text = tweet[i]
					if text == None:
						text = ""
					out += '\t\t"' + field.strip() + '":"' + str(text) + '",\n'
					i += 1
				out = out[:-2] + "\n\t},\n"
			out = out[:-2]+'\n'
			pickle.dump(out, open(signature, "wb"))

		if request.args.get('download'):
			if request.args.get('download') == '1':
				generator = (cell for row in out for cell in row)
				return Response(generator, mimetype="text/plain", headers={"Content-Disposition":"attachment;filename="+out_file+".json"})
			else:
				return out
		else:
			return out

	except Exception as e:
		return 'Error: ' + str(e)

@auth.get_password
def get_pwd(username):
	global out_file
	out_file = username
	if username in REGISTERED:
		return REGISTERED.get(username)
	return None

if __name__ == "__main__":
	app.run(host='0.0.0.0',debug=False,threaded=True)
