# coding: utf-8
from django.shortcuts import render
import time, datetime
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.core.context_processors import csrf
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.models import User
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.utils import simplejson
from django.core.urlresolvers import reverse
from polls.models import *
import pdb
import urllib2, json
from urllib import quote

# pdb.set_trace()

def gen_scope_url():
    APPID = "wx455601ff052bea31" #随手换测试号
    REDIRECT_URI = quote("http://yikf.jiutianwai.com/wechatapp/polls/home?pid=1") #调查系统url
    SCOPE = "snsapi_userinfo"
    url = "https://open.weixin.qq.com/connect/oauth2/authorize?appid=%s&redirect_uri=%s&response_type=code&scope=%s&state=STATE#wechat_redirect"\
    % (APPID, REDIRECT_URI, SCOPE)
    return url
def gen_access_token_url(code):
    APPID = "wx455601ff052bea31"
    SECRET = "647bb7f32155cb2b794337145debf105"
    CODE = code
    url = "https://api.weixin.qq.com/sns/oauth2/access_token?appid=%s&secret=%s&code=%s&grant_type=authorization_code"\
    % (APPID, SECRET, CODE)
    return url
def gen_user_info_url(access_token, openid):
    url = "https://api.weixin.qq.com/sns/userinfo?access_token=%s&openid=%s&lang=zh_CN" % (access_token, openid)
    return url
def get_json_response(url):
    response = urllib2.urlopen(url).read()
    dict_data = json.loads(response)
    return dict_data

def home_page(request):
    if request.method=="POST":
        if request.session.has_key("openid"):
            openid = request.session["openid"]
            nickname = request.session["nickname"]
            print openid
            u, created = PollUser.objects.get_or_create(openid=openid)
            gender = request.POST['gender']
            age = request.POST['age']
            # if not created:
            u.openid = openid
            u.nickname = nickname
            u.gender = int(gender)
            u.age = int(age)
            print u.age
            u.save()
            # json = simplejson.dumps({'success': True})
            # return HttpResponse(json, mimetype='application/json')
            return HttpResponseRedirect("/wechatapp/polls/question?pid=1")
    if request.method=="GET":
        url = gen_scope_url()
        if "code" in request.GET:
            code = request.GET.get("code", "")
            access_token_url = gen_access_token_url(code)
            dict_data = get_json_response(access_token_url)
            access_token = dict_data["access_token"]
            openid = dict_data["openid"]
            user_info_url = gen_user_info_url(access_token, openid)
            user_info = get_json_response(user_info_url)
            nickname = user_info["nickname"]
            request.session["openid"] = openid
            request.session["nickname"] = nickname
            u, created = PollUser.objects.get_or_create(openid=openid)

        pid = request.GET.get("pid")
        q = Question.objects.filter(poll=pid)
        q = [question.id for question in q]
        num = Question.objects.filter(poll=pid).count()
        # p = Poll.objects.get(pk=pid)

        # c = Choice.objects.filter(question=q)
        variables=RequestContext(request, {
            # "p": p,
            "q": q,
            # "c": c,
            "num":len(q),
        })
        # RequestContext(request)
        # return render_to_response('polls/home.html',context_instance=RequestContext(request))
        return render_to_response('polls/index.html', variables)
def get_question(request):
    if request.method=="GET":
        pid = request.GET.get("pid")
        # qid = request.GET.get("qid")
        # q = Question.objects.get(poll=pid, qindex=qindex)
        q = Question.objects.filter(poll=pid).order_by("qindex")
        num = Question.objects.filter(poll=pid).count()
        # question = Question.objects.get(pk=qid)
        # choices = Choice.objects.filter(question=qid)
        # p = Poll.objects.get(pk=pid)
        qid_list = [question.id for question in q]
        # c = Choice.objects.filter(question=q)
        variables=RequestContext(request, {
            "q": qid_list,
            # "c": c,
            "num":len(q),
        })
        return render_to_response("polls/answer_gen.html", variables)

def answer_question(request):
    if request.method=="POST":
        # print request.POST
        pid = request.POST["pid"]
        qid = request.POST["qid"]
        # uid = request.POST["uid"]
        cid = request.POST["cid"]
        openid = request.session["openid"]
        poll = Poll.objects.get(id=pid)
        question = Question.objects.get(id=qid)
        choice = Choice.objects.get(id=cid)
        u = PollUser.objects.get(openid=openid)
        a = Answer.objects.filter(uid=u, pid=poll, qid=question).first()
        if a == None:
            print "111"
            a = Answer.objects.create(uid=u, pid=poll, qid=question, cid=choice)
            print "222"
        else:
            a.cid = choice
        # print created
        # a.cid = choice
            a.save()
        json = simplejson.dumps({'success': True})
        return HttpResponse(json, mimetype="application/json")
    if request.method=="GET":
        qid = request.GET["qid"]
        question = Question.objects.get(pk=qid)
        choices = Choice.objects.filter(question=qid)
        variables = RequestContext(request, {
            "choices": choices,
            "question": question,
            })
        return render_to_response("polls/answer.html", variables)
        # variables = {"choices": choices, "question": question}
        # json = simplejson.dumps(variables)
        # return HttpResponse(json, mimetype="application/json")
def get_result(request):
    '''获取poll下面uid每一个最近的选项作为计分项'''
    if request.method=="GET":
        total = 0
        pid = request.GET.get("pid")
        poll = Poll.objects.get(id=pid)
        openid = request.session["openid"]
        u = PollUser.objects.get(openid=openid)
        a = Answer.objects.filter(uid=u, pid=poll).order_by('-submit_time')
        for answer in a:
            total += answer.cid.score
            print "answer: %s" % answer.cid.score
            answer.cid.votes += 1
        print "total: %s" % total 
        variables = RequestContext(request, {
            "total": total,
        })
        return render_to_response("polls/result.html", variables)

# def response_chart(request):
#     q = Question.objects.all()
#     # c = Choice.objects.all()
#     votes_count = 0
#     user_count = 0
#     for question in q:
#         c = Choice.objects.filter(question=question)
#             for choice in c:
#                 c_count = Answer.objects.filter(cid=c, qid=q).count()
#                 q_count = Answer.objects.filter(qid=q).count()
#                 c_proportion = c_count/q_count

#     return render_to_response("polls/count.html")