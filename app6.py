from flask import Flask 
from flask import flash 
from flask import render_template
from flask import request,redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import session,url_for


app6 = Flask(__name__)

app6.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///mydata.db"#configuration
app6.secret_key="baapnpalnea"
db=SQLAlchemy()


db.init_app(app6)
app6.app_context().push()

# database  part - -------------------------------------------------------------------------------------------
class Userdata(db.Model):
    __tablename__="users"
    user_id=db.Column(db.Integer,primary_key=True,autoincrement=True)
    username=db.Column(db.String(50),unique=True,nullable=False)
    password=db.Column(db.String(100),nullable=False)
    mobile=db.Column(db.String(10),nullable=False)
    pincode=db.Column(db.String(10),nullable=False)

    reservation=db.relationship("ReserveSpot",backref="user",cascade="all, delete-orphan")
    

class Admindata(db.Model):
    __tablename__="admin"
    admin_id=db.Column(db.Integer,primary_key=True,autoincrement=True)
    adminname=db.Column(db.String(50),unique=True,nullable=False)
    adminpassword=db.Column(db.String(100),nullable=False)
    
class Parkinglot(db.Model):
    __tablename__="parkinglot"
    parking_id=db.Column(db.Integer,primary_key=True)
    location=db.Column(db.String(150),nullable=False)
    price=db.Column(db.Integer,nullable=False)
    maxspot=db.Column(db.Integer,nullable=False)
    
    spots = db.relationship("Parkingspot", backref="lot", cascade="all, delete-orphan")
    reservations = db.relationship("ReserveSpot", backref="lot", cascade="all, delete-orphan")

class Parkingspot(db.Model):
    __tablename__="parkingspot"
    spot_id=db.Column(db.Integer,primary_key=True)
    lot_id=db.Column(db.Integer,db.ForeignKey("parkinglot.parking_id"),nullable=False)
    status=db.Column(db.String(9),nullable=False,default="available")

    

class ReserveSpot(db.Model):
    __tablename__="reservespot" 
    reserve_id= db.Column(db.Integer,primary_key=True)
    reservespotid=db.Column(db.Integer,db.ForeignKey("parkinglot.parking_id"),nullable=False)
    reserveuserid=db.Column(db.Integer,db.ForeignKey("users.user_id"),nullable=False)
    parkingtime=db.Column(db.DateTime)
    leavingtime=db.Column(db.DateTime)
    parkingcostperunit=db.Column(db.Float,nullable=False)
    total_cost=db.Column(db.Float)
    reservedspotid = db.Column(db.Integer, db.ForeignKey("parkingspot.spot_id"), nullable=True)
    spot=db.relationship("Parkingspot",backref="reservations")
    vehicle_number = db.Column(db.String(20), nullable=False)
db.create_all()

def create_admin():
    admin_flag = Admindata.query.filter_by(adminname='Chahat').first()
    if not admin_flag:
        admin= Admindata(adminname="Chahat",adminpassword="password")
        db.session.add(admin)
        db.session.commit()
        print ("admin added")
    else:
        print("admin is alredy there")



@app6.route("/")  
def default():
    return render_template("firstpage.html")

    
@app6.route("/login",methods=["GET","POST"])  
def login():
    if request.method=="GET":
        return render_template("login.html")
    if request.method=="POST":
        lusername=request.form.get("user")
        lpassword=request.form.get("pass")
        user_flag=Userdata.query.filter_by(username=lusername).first()
        admin_flag=Admindata.query.filter_by(adminname=lusername).first()
        if admin_flag and  admin_flag.adminpassword==lpassword:
            session["username"]=lusername
            session["role"]="admin"
            return redirect("/admindashboard")
        else:
            if user_flag:
                if user_flag.password==lpassword: 
                    session["username"]=lusername
                    session["role"]="user"
                    print("password is in correct")
                    return redirect(f"/userdashboard/{lusername}")
                else:
                    return render_template("login.html",error="password is incorrect")
            else:
                return redirect("/register")   


@app6.route("/register",methods=["GET","POST"])
def register():
    if request.method=="GET":
        return render_template("register.html")
    else:
        rusername=request.form.get("user")
        rpassword=request.form.get("pass")
        rmobile = request.form.get("mobile")
        rpincode = request.form.get("pincode")

        user_flag=Userdata.query.filter_by(username=rusername).first()
        if user_flag:
            print("Please use different user name")
            return redirect("/register")
        else:
            newuser=Userdata(username=rusername,password=rpassword,mobile=rmobile, pincode=rpincode)
            db.session.add(newuser)
            db.session.commit()
            print("user created successfully")
            return redirect("/login")
    

@app6.route("/userdashboard/<string:username>")
def userdashboard(username):
       user=Userdata.query.filter_by(username=username).first()
       lots=Parkinglot.query.all()
       active_reservation=ReserveSpot.query.filter_by(reserveuserid=user.user_id,leavingtime=None).all()

       return render_template("userdashboard.html",dusername=username,lots=lots,active_reservation=active_reservation) 

@app6.route("/usersummary/<string:username>")
def usersummary(username):
    user = Userdata.query.filter_by(username=username).first()

    chart_data = []
    lots = Parkinglot.query.all()
    for lot in lots:
        reservations = ReserveSpot.query.filter_by(
            reserveuserid=user.user_id, reservespotid=lot.parking_id
        ).count()

        total_cost = db.session.query(
            db.func.sum(ReserveSpot.total_cost)
        ).filter_by(
            reserveuserid=user.user_id, reservespotid=lot.parking_id
        ).scalar() or 0

        chart_data.append({
            "location": lot.location,
            "reservations": reservations,
            "cost": total_cost
        })

    return render_template(
        "usersummary.html",
        dusername=username,
        chart_data=chart_data
    )


@app6.route("/releasebooking",methods=["POST"])
def releasebooking():
    username=session.get("username")
    user=Userdata.query.filter_by(username=username).first()

    reservation_id=request.form.get("reservation_id")
    reservation=ReserveSpot.query.get(reservation_id)

    if not reservation or reservation.reserveuserid != user.user_id or reservation.leavingtime is not None:
        return " already released reservation"

    reservation.leavingtime=datetime.now()
    duration=(reservation.leavingtime- reservation.parkingtime).total_seconds() / 60
    cost=round(duration*reservation.parkingcostperunit,2)
    reservation.total_cost=cost

    spot=Parkingspot.query.get(reservation.reservedspotid)
    if spot:
        spot.status="available"
    db.session.commit()
    return redirect(url_for("bookinghistory"))

@app6.route("/bookinghistory")
def bookinghistory():
    username=session.get("username")
    user=Userdata.query.filter_by(username=username).first()
    released_bookings=ReserveSpot.query.filter_by(reserveuserid=user.user_id).filter(ReserveSpot.leavingtime.isnot(None)).all()
    return render_template("bookinghistory.html",bookings=released_bookings,dusername=username)




@app6.route("/admindashboard")
def admindashboard():
    lots=Parkinglot.query.all()
    reservations=ReserveSpot.query.join(Userdata).join(Parkingspot).all()
    return render_template("admindashboard.html",lots=lots,reservations=reservations)





@app6.route("/createlot", methods=["GET", "POST"])
def createlot():
    if request.method == "GET":
        return render_template("createlot.html")
    if request.method == "POST":
        location = request.form.get("location")
        price = int(request.form.get("price"))
        maxspot = int(request.form.get("maxspot"))

        print(f"Received: location={location}, price={price}, maxspot={maxspot}")

        newlot = Parkinglot(location=location, price=price, maxspot=maxspot)
        db.session.add(newlot)
        db.session.commit()

        print(f"Lot created with ID: {newlot.parking_id}")

        for i in range(maxspot):
            print(f"Adding spot {i+1} for lot {newlot.parking_id}")
            spot = Parkingspot(lot_id=newlot.parking_id, status="available")
            db.session.add(spot)

        db.session.commit()
        print("Parking spots created")
        return redirect("/admindashboard")

@app6.route("/editlot/<int:lot_id>", methods=["GET", "POST"])
def editlot(lot_id):
    lot = Parkinglot.query.get_or_404(lot_id)

    if request.method == "GET":
        return render_template("editlot.html", lot=lot)

    if request.method == "POST":
        location = request.form.get("location")
        price = int(request.form.get("price"))
        new_max = int(request.form.get("maxspot"))

        lot.location = location
        lot.price = price

        # Sync Parkingspot records with new maxspot
        current_spots = Parkingspot.query.filter_by(lot_id=lot_id).all()
        current_count = len(current_spots)

        if new_max > current_count:
            # Add new spots
            for i in range(current_count + 1, new_max + 1):
                new_spot = Parkingspot(lot_id=lot_id, status="available")
                db.session.add(new_spot)

        elif new_max < current_count:
            # Remove extra spots (only those still available)
            extra_spots = current_spots[new_max:]
            for spot in extra_spots:
                if spot.status == "available":
                    db.session.delete(spot)
                else:
                    # If reserved, you may want to block deletion or handle differently
                    pass

        lot.maxspot = new_max
        db.session.commit()

        return redirect("/admindashboard")


@app6.route("/deletelot/<int:lot_id>", methods=["POST"])
def deletelot(lot_id):
    lot=Parkinglot.query.get(lot_id)
    db.session.delete(lot)
    db.session.commit()
    return redirect("/admindashboard")


@app6.route("/bookslot/<int:lot_id>", methods=["GET", "POST"])
def bookslot(lot_id):
    username = session.get("username")
    if not username:
        return redirect("/login")

    user = Userdata.query.filter_by(username=username).first()
    parking_lot = Parkinglot.query.get(lot_id)

    if request.method == "GET":
        firstspot = Parkingspot.query.filter_by(lot_id=lot_id, status="available").first()
        if not firstspot:
            return "NO SPOT available"
        
        start_time = datetime.now()

        # Store spot ID and time temporarily in session
        session["pending_spot_id"] = firstspot.spot_id
        session["pending_start_time"] = start_time.strftime("%Y-%m-%d %H:%M:%S")

        return render_template("book.html",
                               lot_id=lot_id,
                               lot_name=parking_lot.location,
                               spot_id=firstspot.spot_id,
                               start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                               cost=parking_lot.price)

    

    elif request.method == "POST":
        vehicle_number = request.form.get("vehicle_number")
        spot_id = session.get("pending_spot_id")
        pending_start_time = session.get("pending_start_time")

    if not spot_id or not pending_start_time:
        # Defensive fallback: redirect or show error
        flash("Booking session expired. Please try again.", "error")
        return redirect(url_for("userdashboard", username=username))

    start_time = datetime.strptime(pending_start_time, "%Y-%m-%d %H:%M:%S")

    reservation = ReserveSpot(
        reservespotid=lot_id,
        reserveuserid=user.user_id,
        reservedspotid=spot_id,
        vehicle_number=vehicle_number,
        parkingtime=start_time,
        parkingcostperunit=parking_lot.price
    )
    db.session.add(reservation)

    spot = Parkingspot.query.get(spot_id)
    spot.status = "reserved"

    db.session.commit()

    session.pop("pending_spot_id", None)
    session.pop("pending_start_time", None)

    return redirect(url_for("userdashboard", username=username))

@app6.route("/logout")
def logout():
    session.clear()
    return redirect("/login")




if __name__ == "__main__":
    create_admin()
    app6.run(debug=True)