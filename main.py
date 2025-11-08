from flask import Flask, render_template, request, Blueprint, redirect, url_for, flash
from routes.sobre import sobre_route
from models import Usuario, Flights, Settings, Family
from db import db
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from bs4 import BeautifulSoup
import requests
from datetime import datetime, date, timedelta
import hashlib
from flask_apscheduler import APScheduler
import smtplib
import email.message
  
class Config:
    SCHEDULER_API_ENABLED = True
app = Flask(__name__)
app.secret_key = 'azulzinhoplays'
lm = LoginManager(app)
database = "postgresql://decolandohistorias_host:F8JZ4vzpn6kePB4XKpYiP6c0YbN1S5i2@dpg-d47ocjqli9vc738shaig-a.oregon-postgres.render.com/decolandohistorias_database_fmhk"
app.config["SQLALCHEMY_DATABASE_URI"] = database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_RECYCLE'] = 300
app.config['SQLALCHEMY_POOL_SIZE'] = 10
db.init_app(app)
lm.login_view = 'login'
scheduler = APScheduler()
def hash(txt):
    hash_obj = hashlib.sha256(txt.encode('utf-8'))
    return hash_obj.hexdigest()
@app.route("/teste_log")
def teste_log():
    if current_user.is_authenticated:
        return redirect(url_for('client_home'))
    else:
        return redirect(url_for('login'))
@lm.user_loader
def user_loader(id):
    usuario = db.session.query(Usuario).filter_by(id=id).first()
    return usuario
@app.route("/")
def home():
    return render_template("home.html")
@app.route("/home", methods=["GET","POST"])
@login_required
def client_home():
    voos = Flights.query.filter_by(user_id=current_user.id).first()
    if voos:
        viagem = True
        agora = datetime.now()
        voos_organizados = Flights.query.order_by(Flights.date.desc(), Flights.horario_saida.asc()).all()
        next_flight = Flights.query.order_by(Flights.date.desc(), Flights.horario_saida.asc()).first()
        return render_template("cliente_home.html", viagem=viagem, next_flight=next_flight, voos_organisados=voos_organizados)
    else:
        return render_template("cliente_home.html")
app.register_blueprint(sobre_route, url_prefix='/sobre')
@app.route("/register", methods=["GET","POST"])
def registrar():      
    if request.method=="GET":
        return render_template("registrar.html")
    elif request.method=="POST":
        email = request.form["emailForm"]
        nome = request.form["nameForm"]
        senha = request.form["pwdForm"]
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            return render_template("registrar.html", user_exist=usuario_existente)
        else:
            novo_usuario = Usuario(email=email, nome=nome, senha=hash(senha))
            db.session.add(novo_usuario)
            db.session.commit()
            login_user(novo_usuario)
            return redirect(url_for('client_home'))
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="GET":
        return render_template("login.html")
    elif request.method=="POST":
        email = request.form["emailForm"]
        senha = request.form["pwdForm"]
        user = db.session.query(Usuario).filter_by(email=email, senha=hash(senha)).first()
        if not user:
            incorreto = True
            return render_template("login.html", incorreto=incorreto)
        else:
            login_user(user)
            return redirect(url_for('client_home'))
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))
@app.route("/profile/", methods=["GET","POST"])
@login_required
def profile():
    if request.method=="GET":
        return render_template("profile.html")
    elif request.method=="POST":
        profile_cor = request.form["profile_cor"]
        user_log = current_user
        if user_log:
            user_log.profile_cor = profile_cor
            db.session.commit()
            return render_template("profile.html")
@app.route("/edit", methods=["GET","POST"])
def edit():
    if request.method == "GET":
        return render_template("edit_name.html")
    elif request.method == "POST":
        nome = request.form["nome"]
        user_log = current_user
        if user_log:
            user_log.nome = nome
            db.session.commit()
            return redirect(url_for('profile'))
@app.route("/home/register_flight", methods=["GET","POST"])
@login_required
def registrar_voo():
    if request.method == "GET":
        return render_template("registrar_voo.html")
    elif request.method == "POST":
        numero_voo = request.form["numForm"]
        data_voo = request.form["dateForm"]
        data_voo_data = datetime.strptime(data_voo, "%Y-%m-%d")
        url = f'https://planeslive.com/flight/{numero_voo}'
        headers = {"User_Agent" :"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"}
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.text,'html.parser')
        try:    
            departure = soup.find("p", class_="flightCard_title__zl44d")
            Departure = departure.get_text()
            arrival = soup.find_all("p", class_="flightCard_title__zl44d")[1]
            Arrival = arrival.get_text()
            departure_iata = soup.find("p", class_="FlightPreview_iata__z3L3g")
            Departure_Iata = departure_iata.get_text()
            arrival_iata = soup.find_all("p", class_="FlightPreview_iata__z3L3g")[1]
            Arrival_Iata = arrival_iata.get_text()
            tempo_voo = soup.find_all('p', class_="FlightPreview_distance__wf0dH")[1]
            Tempo_Voo = tempo_voo.get_text()
            horario_saida = soup.find("p", class_="time_onTime__c2gb5")
            Horario_Saida = horario_saida.get_text()
            horario_chegada = soup.find_all("p", class_="time_onTime__c2gb5")[1]
            Horario_Chegada = horario_chegada.get_text()
            status = soup.find("p", class_="time_text__JmblB")
            Status = status.get_text()
            terminal = soup.find_all("p", class_="infoBlock_label__MOn_6")[1]
            gate = soup.find("div", class_="gate_container__APCdI")
            data_string_original = data_voo
            partes = data_string_original.split('-')
            partes.reverse()
            data_invertida = '-'.join(partes)
            adcionar_voo = Flights(user_id=current_user.id, departure=Departure, arrival=Arrival, number=numero_voo, date=data_invertida, arrival_iata=Arrival_Iata, departure_iata=Departure_Iata, tempo_voo=Tempo_Voo, horario_saida=Horario_Saida, horario_chegada=Horario_Chegada)
            db.session.add(adcionar_voo)
            db.session.commit()
            adcionou = True
            data_voo_data = datetime.strptime(data_voo, "%Y-%m-%d")
            Horario_Saida_Data = datetime.strptime(Horario_Saida, "%I:%M %p")
            Horario_Saida_Data_3h = Horario_Saida_Data - timedelta(hours=3)
            proximo_voo = Flights.query.order_by(Flights.date.desc(), Flights.horario_saida.asc()).first()
            email_user = current_user.email
            print(email_user)
            print(f"{data_voo_data.year} {Horario_Saida_Data_3h.hour}")
            def email_3h():
                corpo_email = f"""
                    <h1>Faltam exatamente 3h para o voo {proximo_voo.number}!</h1> 
                    <hr>
                    <h3>Se prepare para chegar no aeroporto de {proximo_voo.departure} em pelo menos 30 minutos!</h3>
                    <hr>
                    <h3>Seu terminal e: {terminal}</h3>
                    <h3>Seu gate nao esta disponivel agora.</h3>
                    <hr>
                    <h2>Aproveite sua viagem!</h2>
                """
                msg = email.message.Message()
                msg['Subject'] = f"Voo {proximo_voo.number}"
                msg['From'] = 'decolandohistorias@gmail.com'
                msg['To'] = f'{email_user}'
                password = 'gsusxjiawpwcpvjn' 
                msg.add_header('Content-Type', 'text/html')
                msg.set_payload(corpo_email)
                s = smtplib.SMTP('smtp.gmail.com: 587')
                s.starttls()
                # Login Credentials for sending the mail
                s.login(msg['From'], password)
                s.sendmail(msg['From'], [msg['To']], msg.as_string().encode('utf-8'))
            @scheduler.task(
                'date',
                id='email_3h',
                run_date=datetime(
                    data_voo_data.year, data_voo_data.month, data_voo_data.day, Horario_Saida_Data_3h.hour, Horario_Saida_Data.minute, 0
                )
            )
            def Tarefa():
                email_3h()
            return render_template("registrar_voo.html", adcionou=adcionou)
        except:
            erro = True
            return render_template("registrar_voo.html", erro=erro)
@app.route("/home/register_flight/info")
def info():
    return render_template("info_num.html")
@app.route("/home/delete_flight/<int:id>")
@login_required
def delete_flight(id):
    flight = Flights.query.get(id)
    db.session.delete(flight)
    db.session.commit()
    return redirect(url_for('client_home'))
@app.route("/settings", methods=["GET","POST"])
@login_required
def settings():
    return render_template("pagina_construcao.html")
# if request.method == "GET":
#     return render_template("settings.html")
# elif request.method == "POST":
#     voo_checked = True if request.form.get('voo_check') else False
#     if current_user.is_authenticated:
#         current_user.mostrar_sem_voos = voo_checked
#         db.session.commit()
#         return 'Configurações salvas com sucesso!'
#     else:
#         return 'Você precisa estar logado para salvar as configurações.', 401
@login_required
@app.route("/family")
def familia():
    Familia = Family.query.filter_by(user_id=current_user.id).first()
    if Familia:
        Familia = True
        return render_template("familia.html", Familia=Familia)
    else:
        Familia = False
        return render_template("familia.html", Familia=Familia)
@login_required
@app.route("/adcionar_familiar", methods=["GET","POST"])
def adcionar_pessoa():
    if request.method == "GET":
        return render_template("adcionar_pessoa.html")
if __name__=='__main__':    
    with app.app_context():
         db.create_all()
    scheduler.init_app(app)
    scheduler.start()
    app.run(debug=True)


