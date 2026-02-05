import threading
import requests
import hashlib
import json
import time
import os

# Kivy Imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.properties import StringProperty

# Crypto Imports
from mnemonic import Mnemonic
from ecdsa import SigningKey, SECP256k1

# Configuration
NODE_URL = "http://13.220.55.223:80/api" # Using the public proxy
WALLET_FILE = "my_wallet.json"

class WalletManager:
    @staticmethod
    def create_wallet():
        mnemo = Mnemonic("english")
        words = mnemo.generate(strength=128) # 12 words
        seed = mnemo.to_seed(words)
        sk = SigningKey.from_string(seed[:32], curve=SECP256k1)
        address = sk.verifying_key.to_string().hex()
        return words, address, sk.to_pem()

    @staticmethod
    def import_wallet(words_str):
        mnemo = Mnemonic("english")
        if not mnemo.check(words_str):
            return None, None, None
        seed = mnemo.to_seed(words_str)
        sk = SigningKey.from_string(seed[:32], curve=SECP256k1)
        address = sk.verifying_key.to_string().hex()
        return words_str, address, sk.to_pem()

    @staticmethod
    def save_wallet(data):
        # We save the PEM for mining, and words for recovery if needed (optional)
        # For security, standard apps restrict access. Here we save locally.
        with open(WALLET_FILE, "w") as f:
            json.dump(data, f)

    @staticmethod
    def load_wallet():
        if os.path.exists(WALLET_FILE):
            try:
                with open(WALLET_FILE, "r") as f:
                    return json.load(f)
            except:
                return None
        return None

class WelcomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        layout.add_widget(Label(text="[b]HomeChain Miner[/b]", markup=True, font_size='24sp', size_hint_y=0.2))
        layout.add_widget(Label(text="Mining made simple.\nCreate a new wallet or import\nyour 12-word seed phrase.", halign='center'))
        
        btn_create = Button(text="CREATE NEW WALLET", size_hint_y=None, height=50, background_color=(0, 0.7, 1, 1))
        btn_create.bind(on_press=self.create_wallet)
        layout.add_widget(btn_create)
        
        btn_import = Button(text="IMPORT EXISTING WALLET", size_hint_y=None, height=50, background_color=(0, 0.5, 0.5, 1))
        btn_import.bind(on_press=self.go_import)
        layout.add_widget(btn_import)
        
        self.add_widget(layout)

    def create_wallet(self, instance):
        words, address, pem = WalletManager.create_wallet()
        WalletManager.save_wallet({"words": words, "address": address, "key": pem.decode('utf-8')})
        self.manager.current = 'dashboard'

    def go_import(self, instance):
        self.manager.current = 'import'

class ImportScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add_widget(Label(text="Enter 12-Word Phrase", font_size='18sp', size_hint_y=None, height=40))
        
        self.input_words = TextInput(hint_text="apple banana cat ...", multiline=True, size_hint_y=0.4)
        layout.add_widget(self.input_words)
        
        self.lbl_error = Label(text="", color=(1, 0, 0, 1), size_hint_y=None, height=30)
        layout.add_widget(self.lbl_error)
        
        btn_confirm = Button(text="IMPORT WALLET", size_hint_y=None, height=50)
        btn_confirm.bind(on_press=self.do_import)
        layout.add_widget(btn_confirm)
        
        btn_back = Button(text="BACK", size_hint_y=None, height=50)
        btn_back.bind(on_press=self.go_back)
        layout.add_widget(btn_back)
        
        self.add_widget(layout)

    def do_import(self, instance):
        words = self.input_words.text.strip().lower()
        w, addr, pem = WalletManager.import_wallet(words)
        if w:
            WalletManager.save_wallet({"words": w, "address": addr, "key": pem.decode('utf-8')})
            self.manager.current = 'dashboard'
        else:
            self.lbl_error.text = "Invalid mnemonic phrase!"

    def go_back(self, instance):
        self.manager.current = 'welcome'

class DashboardScreen(Screen):
    status_text = StringProperty("Idle")
    hashrate_text = StringProperty("0.00 H/s")
    balance_text = StringProperty("0.00 HOME")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mining = False
        self.thread = None
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Header
        layout.add_widget(Label(text="[b]DASHBOARD[/b]", markup=True, font_size='20sp', size_hint_y=None, height=40))
        
        # Wallet Info
        self.lbl_address = Label(text="Addr: Loading...", font_size='14sp', size_hint_y=None, height=30, color=(0.7, 0.7, 0.7, 1))
        layout.add_widget(self.lbl_address)
        
        # Balance
        self.lbl_balance = Label(text=self.balance_text, font_size='32sp', bold=True, size_hint_y=None, height=80, color=(0, 1, 0.5, 1))
        layout.add_widget(self.lbl_balance)
        
        # Status Area
        status_box = BoxLayout(orientation='vertical', padding=10, size_hint_y=0.3)
        status_box.add_widget(Label(text=self.status_text))
        status_box.add_widget(Label(text=self.hashrate_text))
        layout.add_widget(status_box)
        
        # Controls
        self.btn_start = Button(text="START MINING 🚀", size_hint_y=None, height=60, background_color=(0, 0.8, 0, 1))
        self.btn_start.bind(on_press=self.toggle_mining)
        layout.add_widget(self.btn_start)
        
        btn_copy = Button(text="Copy Address", size_hint_y=None, height=40)
        btn_copy.bind(on_press=self.copy_address)
        layout.add_widget(btn_copy)

        self.add_widget(layout)
        
        Clock.schedule_interval(self.update_ui, 1.0)

    def on_enter(self):
        data = WalletManager.load_wallet()
        if data:
            self.address = data['address']
            self.lbl_address.text = f"Addr: {self.address[:10]}...{self.address[-8:]}"
            self.status_text = "Ready to mine."
            
    def copy_address(self, instance):
        if hasattr(self, 'address'):
            Clipboard.copy(self.address)
            self.status_text = "Address copied!"

    def toggle_mining(self, instance):
        if not self.mining:
            self.mining = True
            self.btn_start.text = "STOP MINING 🛑"
            self.btn_start.background_color = (1, 0, 0, 1)
            self.thread = threading.Thread(target=self.mine_loop)
            self.thread.daemon = True
            self.thread.start()
        else:
            self.mining = False
            self.btn_start.text = "START MINING 🚀"
            self.btn_start.background_color = (0, 0.8, 0, 1)
            self.status_text = "Stopping..."

    def update_ui(self, dt):
        self.lbl_balance.text = self.balance_text
        # Logic to fetch balance from API could be added here periodically

    def mine_loop(self):
        self.status_text = "Connecting to Node..."
        while self.mining:
            try:
                # 1. Get Work
                r = requests.get(f"{NODE_URL}/mining/get-work?address={self.address}&device_id=ANDROID_USER", timeout=5)
                if r.status_code != 200:
                    time.sleep(2)
                    continue
                
                work = r.json()
                target = work['target']
                idx = work['index']
                
                self.status_text = f"Mining Block #{idx}..."
                
                # Mining Algo
                nonce = 0
                start_t = time.time()
                
                while self.mining:
                    # periodically check for new block
                    if time.time() - start_t > 15:
                        break
                        
                    txs = json.dumps(work['transactions'], sort_keys=True)
                    s = f"{idx}{work['previous_hash']}{work['timestamp']}{txs}{self.address}{nonce}"
                    h = hashlib.sha256(s.encode()).hexdigest()
                    
                    if int(h, 16) < target:
                        self.status_text = "Found Block! Submitting..."
                        submit_data = work.copy()
                        submit_data['nonce'] = nonce
                        submit_data['validator'] = self.address
                        requests.post(f"{NODE_URL}/mining/submit", json=submit_data)
                        self.status_text = "Block Accepted! 💰"
                        time.sleep(1)
                        break
                        
                    nonce += 1
                    if nonce % 5000 == 0:
                        elapsed = time.time() - start_t
                        if elapsed > 0:
                            self.hashrate_text = f"{int(nonce/elapsed)} H/s"
                            
            except Exception as e:
                self.status_text = "Network Error (Retrying...)"
                time.sleep(3)

class HomeChainApp(App):
    def build(self):
        sm = ScreenManager()
        
        # Check if wallet exists
        if WalletManager.load_wallet():
            sm.add_widget(DashboardScreen(name='dashboard'))
            sm.add_widget(WelcomeScreen(name='welcome'))
            sm.add_widget(ImportScreen(name='import'))
        else:
            sm.add_widget(WelcomeScreen(name='welcome'))
            sm.add_widget(ImportScreen(name='import'))
            sm.add_widget(DashboardScreen(name='dashboard'))
            
        return sm

if __name__ == '__main__':
    HomeChainApp().run()
