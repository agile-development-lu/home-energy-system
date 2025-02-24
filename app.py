import time
import uuid
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash

# ========== 1. 核心类定义 ==========

class Grid:
    """固定价格收购，数量无限。"""
    def __init__(self, grid_price=0.3):
        self.grid_price = grid_price

    def buy_energy(self, quantity):
        total = quantity * self.grid_price
        print(f"[Grid] Buy {quantity} kWh at {self.grid_price} => total={total:.2f}")
        return total

class EnglishAuction:
    def __init__(self, auction_id, quantity, grid_price=0.3,
                 start_price=0.0,
                 total_duration=3600, extension_duration=300):
        self.auction_id = auction_id
        self.quantity = quantity
        self.grid = Grid(grid_price)

        # 拍卖起始价
        self.start_price = start_price
        self.highest_bid = start_price  # <--- 初始化最高价=起始价

        self.total_duration = total_duration
        self.extension_duration = extension_duration
        self.start_time = time.time()

        self.highest_bidder = None
        self.last_bid_time = None

        self.auction_ended = False
        self.canceled = False

    def place_bid(self, bidder_name, bid_price):
        if self.auction_ended:
            return {"status": "fail", "msg": "Auction ended already"}
        if self.canceled:
            return {"status": "fail", "msg": "Auction canceled by seller"}
        if bid_price <= self.highest_bid:
            return {
                "status": "fail",
                "msg": f"Bid {bid_price} not higher than current {self.highest_bid}"
            }

        self.highest_bid = bid_price
        self.highest_bidder = bidder_name
        self.last_bid_time = time.time()
        return {"status": "success", "msg": f"New highest bid={bid_price} by {bidder_name}"}

    def get_remaining_time(self):
        if self.auction_ended or self.canceled:
            return 0

        total_remaining = (self.start_time + self.total_duration) - time.time()

        # 若无人出价 => extension_remaining = total_remaining
        if self.last_bid_time is None:
            extension_remaining = total_remaining
        else:
            extension_remaining = (self.last_bid_time + self.extension_duration) - time.time()

        return max(0, max(total_remaining, extension_remaining))

    def check_if_ended(self):
        if self.auction_ended or self.canceled:
            return

        now = time.time()
        # 若超总时长
        if now > self.start_time + self.total_duration:
            self.auction_ended = True
            self._finalize_auction()
            return

        # 若有人出价过 且超了延长时长
        if self.last_bid_time and (now > self.last_bid_time + self.extension_duration):
            self.auction_ended = True
            self._finalize_auction()

    def _finalize_auction(self):
        if self.highest_bid >= self.grid.grid_price and self.highest_bidder:
            print(f"[Auction {self.auction_id}] Ended. Winner={self.highest_bidder}, Price={self.highest_bid}")
        else:
            cost = self.grid.buy_energy(self.quantity)
            print(f"[Auction {self.auction_id}] Ended. Sold to Grid => cost={cost:.2f}")

    def get_status(self):
        st = "ended" if self.auction_ended or self.canceled else "ongoing"
        time_left = self.get_remaining_time()
        status_dict = {
            "auction_id": self.auction_id,
            "quantity": self.quantity,
            "total_duration": self.total_duration,
            "extension_duration": self.extension_duration,
            "start_time": self.start_time,
            "highest_bid": self.highest_bid,
            "highest_bidder": self.highest_bidder,
            "time_left": time_left,
            "status": st
        }

        if self.canceled:
            status_dict["winner"] = "Canceled"
        elif self.auction_ended:
            if self.highest_bid >= self.grid.grid_price and self.highest_bidder:
                status_dict["winner"] = self.highest_bidder
                status_dict["price"] = self.highest_bid
            else:
                status_dict["winner"] = "Grid"
                status_dict["price"] = self.grid.grid_price

        return status_dict

class AuctionManager:
    def __init__(self):
        self.auctions = {}
        self.auction_seller_map = {}

    def create_auction(self, seller_id, quantity, grid_price=0.3,
                       start_price=0.0,
                       total_duration=3600, extension_duration=300):
        auction_id = str(uuid.uuid4())[:8]
        auc = EnglishAuction(
            auction_id=auction_id,
            quantity=quantity,
            grid_price=grid_price,
            start_price=start_price,   # <-- 关键：传给EnglishAuction
            total_duration=total_duration,
            extension_duration=extension_duration
        )
        self.auctions[auction_id] = auc
        self.auction_seller_map[auction_id] = seller_id
        print(f"[Manager] Created Auction {auction_id} by Seller {seller_id}, start_price={start_price}")
        return auction_id

    def get_auction(self, auction_id):
        return self.auctions.get(auction_id)

    def cancel_auction(self, auction_id, seller_id):
        auc = self.auctions.get(auction_id)
        if not auc:
            return {"status": "fail", "msg": "Auction not found"}
        if self.auction_seller_map.get(auction_id) != seller_id:
            return {"status": "fail", "msg": "Not your auction"}
        if auc.auction_ended or auc.canceled:
            return {"status": "fail", "msg": "Auction ended/canceled already."}

        auc.canceled = True
        auc.auction_ended = True
        return {"status": "success", "msg": f"Auction {auction_id} canceled."}

    def list_all_auctions(self):
        return [auc.get_status() for auc in self.auctions.values()]

    def list_seller_auctions(self, seller_id):
        return [
            self.auctions[aid].get_status()
            for aid, sid in self.auction_seller_map.items()
            if sid == seller_id
        ]

    def check_all_auctions(self):
        for aid, auc in self.auctions.items():
            if not auc.auction_ended and not auc.canceled:
                auc.check_if_ended()
                if auc.auction_ended or auc.canceled:
                    # 拍卖刚结束 => 广播
                    socketio.emit("auction_status", auc.get_status(), room=aid)


# ========== 2. 全局实例和初始化 ==========

manager = AuctionManager()
app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!123"
socketio = SocketIO(app, async_mode="eventlet")


# ========== 3. 用户管理系统 ==========

class UserManager:
    def __init__(self):
        # 初始化一个admin
        self.users = {
            "admin": {
                "password": generate_password_hash("admin123")
            }
        }

    def add_user(self, username, password):
        if username in self.users:
            return False
        self.users[username] = {
            "password": generate_password_hash(password)
        }
        return True

    def verify_user(self, username, password):
        user = self.users.get(username)
        if user and check_password_hash(user["password"], password):
            return user
        return None

user_manager = UserManager()


# ========== 4. Flask 路由 ==========

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = user_manager.verify_user(username, password)
        if user:
            session["user"] = username
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if user_manager.add_user(username, password):
            return redirect(url_for("login"))
        return render_template("register.html", error="Username exists")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/buyer_main.html")
def buyer_main():
    return render_template("buyer_main.html")

@app.route("/buyer_detail.html")
def buyer_detail():
    return render_template("buyer_detail.html")

@app.route("/seller_main.html")
def seller_main():
    return render_template("seller_main.html")


# ========== 5. REST API接口 ==========

@app.route("/api/list_auctions", methods=["GET"])
def list_auctions_api():
    data = manager.list_all_auctions()
    return jsonify(data)

@app.route("/api/create_auction", methods=["POST"])
def create_auction_api():
    # 如果没登录, 返回JSON而非跳转HTML
    if "user" not in session or not session["user"]:
        return jsonify({"status":"fail","msg":"Please login first"}), 401

    payload = request.json if request.is_json else request.form
    quantity = float(payload.get("quantity", 10))
    grid_price = float(payload.get("grid_price", 0.3))
    start_price = float(payload.get("start_price", 0.0))
    total_duration = int(payload.get("total_duration", 3600))
    extension_duration = int(payload.get("extension_duration", 300))

    seller_id = session["user"]
    aid = manager.create_auction(
        seller_id=seller_id,
        quantity=quantity,
        grid_price=grid_price,
        start_price=start_price,
        total_duration=total_duration,
        extension_duration=extension_duration
    )
    return jsonify({"status":"success","auction_id":aid})

@app.route("/api/list_seller_auctions", methods=["GET"])
def list_seller_auctions_api():
    # 若未登录, 直接返回json
    if "user" not in session or not session["user"]:
        return jsonify({"status":"fail","msg":"Please login first"}), 401
    seller_id = session["user"]
    data = manager.list_seller_auctions(seller_id)
    return jsonify(data)


# ========== 6. SocketIO事件处理 ==========

@socketio.on("join_auction")
def handle_join_auction(data):
    auction_id = data.get("auction_id")
    if auction_id not in manager.auctions:
        emit("error", {"msg": f"Auction {auction_id} not found"})
        return
    join_room(auction_id)
    st = manager.get_auction(auction_id).get_status()
    emit("auction_status", st, room=auction_id)

@socketio.on("place_bid")
def handle_place_bid(data):
    auction_id = data.get("auction_id")
    bid_price = data.get("bid_price", 0)
    # 若未登录
    if "user" not in session or not session["user"]:
        emit("bid_response", {"status":"fail","msg":"Please login first"})
        return

    bidder_name = session["user"]
    auc = manager.get_auction(auction_id)
    if not auc:
        emit("bid_response", {"status": "fail", "msg": "Auction not found"})
        return

    res = auc.place_bid(bidder_name, float(bid_price))
    emit("bid_response", res)

    if res["status"] == "success":
        socketio.emit("auction_status", auc.get_status(), room=auction_id)


# ========== 7. 后台监控线程 ==========
def background_monitor():
    while True:
        socketio.sleep(3)
        manager.check_all_auctions()
        # 推送全局拍卖列表更新
        socketio.emit("auction_list_update", manager.list_all_auctions())

socketio.start_background_task(background_monitor)


# ========== 8. 启动入口 ==========
if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
