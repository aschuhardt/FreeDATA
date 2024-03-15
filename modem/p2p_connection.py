import threading
from enum import Enum
from modem_frametypes import FRAME_TYPE
from codec2 import FREEDV_MODE
import data_frame_factory
import structlog
import random
from queue import Queue

class States(Enum):
    NEW = 0
    CONNECTING = 1
    CONNECT_SENT = 2
    CONNECT_ACK_SENT = 3
    CONNECTED = 4
    HEARTBEAT_SENT = 5
    HEARTBEAT_ACK_SENT = 6
    PAYLOAD_SENT = 7
    DISCONNECTING = 8
    DISCONNECTED = 9
    FAILED = 10



class P2PConnection:
    STATE_TRANSITION = {
        States.NEW: {
            FRAME_TYPE.P2P_CONNECTION_CONNECT.value: 'connected_irs',
        },
        States.CONNECTING: {
            FRAME_TYPE.P2P_CONNECTION_CONNECT_ACK.value: 'connected_iss',
        },
        States.CONNECTED: {
            FRAME_TYPE.P2P_CONNECTION_CONNECT.value: 'connected_irs',
            FRAME_TYPE.P2P_CONNECTION_CONNECT_ACK.value: 'connected_iss',
            FRAME_TYPE.P2P_CONNECTION_PAYLOAD.value: 'received_data',
            FRAME_TYPE.P2P_CONNECTION_DISCONNECT.value: 'received_disconnect',
        },
        States.PAYLOAD_SENT: {
            FRAME_TYPE.P2P_CONNECTION_PAYLOAD_ACK.value: 'process_data_queue',
        },
        States.DISCONNECTING: {
            FRAME_TYPE.P2P_CONNECTION_DISCONNECT_ACK.value: 'received_disconnect_ack',
        },
        States.DISCONNECTED: {
            FRAME_TYPE.P2P_CONNECTION_DISCONNECT.value: 'received_disconnect',
            FRAME_TYPE.P2P_CONNECTION_DISCONNECT_ACK.value: 'received_disconnect_ack',

        },
    }

    def __init__(self, config: dict, modem, origin: str, destination: str, state_manager):
        self.logger = structlog.get_logger(type(self).__name__)
        self.config = config
        self.frame_factory = data_frame_factory.DataFrameFactory(self.config)

        self.destination = destination
        self.origin = origin
        self.states = state_manager
        self.modem = modem

        self.p2p_rx_queue = Queue()
        self.p2p_tx_queue = Queue()


        self.state = States.NEW
        self.session_id = self.generate_id()

        def generate_random_string(min_length, max_length):
            import string
            length = random.randint(min_length, max_length)
            return ''.join(random.choices(string.ascii_letters, k=length))

        # Generate and add 5 random entries to the queue
        for _ in range(1):
            random_entry = generate_random_string(2, 11)
            self.p2p_tx_queue.put(random_entry)




        self.event_frame_received = threading.Event()

        self.RETRIES_CONNECT = 1
        self.TIMEOUT_CONNECT = 10
        self.TIMEOUT_DATA = 5
        self.RETRIES_DATA = 5
        self.ENTIRE_CONNECTION_TIMEOUT = 100

        self.is_ISS = False # Indicator, if we are ISS or IRS

    def generate_id(self):
        while True:
            random_int = random.randint(1,255)
            if random_int not in self.states.p2p_connection_sessions:
                return random_int

            if len(self.states.p2p_connection_sessions) >= 255:
                return False


    def set_details(self, snr, frequency_offset):
        self.snr = snr
        self.frequency_offset = frequency_offset

    def log(self, message, isWarning = False):
        msg = f"[{type(self).__name__}][id={self.session_id}][state={self.state}][ISS={bool(self.is_ISS)}]: {message}"
        logger = self.logger.warn if isWarning else self.logger.info
        logger(msg)

    def set_state(self, state):
        if self.state == state:
            self.log(f"{type(self).__name__} state {self.state.name} unchanged.")
        else:
            self.log(f"{type(self).__name__} state change from {self.state.name} to {state.name}")
        self.state = state

    def on_frame_received(self, frame):
        self.event_frame_received.set()
        self.log(f"Received {frame['frame_type']}")
        frame_type = frame['frame_type_int']
        if self.state in self.STATE_TRANSITION:
            if frame_type in self.STATE_TRANSITION[self.state]:
                action_name = self.STATE_TRANSITION[self.state][frame_type]
                response = getattr(self, action_name)(frame)

                return

        self.log(f"Ignoring unknown transition from state {self.state.name} with frame {frame['frame_type']}")

    def transmit_frame(self, frame: bytearray, mode='auto'):
        self.log("Transmitting frame")
        if mode in ['auto']:
            mode = self.get_mode_by_speed_level(self.speed_level)

        self.modem.transmit(mode, 1, 1, frame)

    def transmit_wait_and_retry(self, frame_or_burst, timeout, retries, mode):
        while retries > 0:
            self.event_frame_received = threading.Event()
            if isinstance(frame_or_burst, list): burst = frame_or_burst
            else: burst = [frame_or_burst]
            for f in burst:
                self.transmit_frame(f, mode)
            self.event_frame_received.clear()
            self.log(f"Waiting {timeout} seconds...")
            if self.event_frame_received.wait(timeout):
                return
            self.log("Timeout!")
            retries = retries - 1

        self.session_failed()

    def launch_twr(self, frame_or_burst, timeout, retries, mode):
        twr = threading.Thread(target = self.transmit_wait_and_retry, args=[frame_or_burst, timeout, retries, mode], daemon=True)
        twr.start()

    def transmit_and_wait_irs(self, frame, timeout, mode):
        self.event_frame_received.clear()
        self.transmit_frame(frame, mode)
        self.log(f"Waiting {timeout} seconds...")
        #if not self.event_frame_received.wait(timeout):
        #    self.log("Timeout waiting for ISS. Session failed.")
        #    self.transmission_failed()

    def launch_twr_irs(self, frame, timeout, mode):
        thread_wait = threading.Thread(target = self.transmit_and_wait_irs,
                                       args = [frame, timeout, mode], daemon=True)
        thread_wait.start()

    def connect(self):
        self.set_state(States.CONNECTING)
        self.is_ISS = True
        session_open_frame = self.frame_factory.build_p2p_connection_connect(self.origin, self.destination, self.session_id)
        self.launch_twr(session_open_frame, self.TIMEOUT_CONNECT, self.RETRIES_CONNECT, mode=FREEDV_MODE.signalling)
        return

    def connected_iss(self, frame):
        self.log("CONNECTED ISS...........................")
        self.set_state(States.CONNECTED)
        self.is_ISS = True
        self.process_data_queue()

    def connected_irs(self, frame):
        self.log("CONNECTED IRS...........................")
        self.set_state(States.CONNECTED)
        self.is_ISS = False
        session_open_frame = self.frame_factory.build_p2p_connection_connect_ack(self.destination, self.origin, self.session_id)
        self.launch_twr_irs(session_open_frame, self.ENTIRE_CONNECTION_TIMEOUT, mode=FREEDV_MODE.signalling)

    def session_failed(self):
        self.log("FAILED...........................")
        self.set_state(States.FAILED)

    def process_data_queue(self, frame=None):
        if not self.p2p_tx_queue.empty():
            print("processing data....")

            self.set_state(States.PAYLOAD_SENT)
            data = self.p2p_tx_queue.get()
            sequence_id = random.randint(0,255)
            data = data.encode('utf-8')

            if len(data) <= 11:
                mode = FREEDV_MODE.signalling

            payload = self.frame_factory.build_p2p_connection_payload(mode, self.session_id, sequence_id, data)
            self.launch_twr(payload, self.TIMEOUT_DATA, self.RETRIES_DATA,
                            mode=mode)
            return
        print("ALL DATA SENT!!!!!")
        self.disconnect()

    def prepare_data_chunk(self, data, mode):
        return data

    def received_data(self, frame):
        print(frame)
        ack_data = self.frame_factory.build_p2p_connection_payload_ack(self.session_id, 0)
        self.launch_twr_irs(ack_data, self.ENTIRE_CONNECTION_TIMEOUT, mode=FREEDV_MODE.signalling)

    def transmit_data_ack(self, frame):
        print(frame)

    def disconnect(self):
        self.set_state(States.DISCONNECTING)
        disconnect_frame = self.frame_factory.build_p2p_connection_disconnect(self.session_id)
        self.launch_twr(disconnect_frame, self.TIMEOUT_CONNECT, self.RETRIES_CONNECT, mode=FREEDV_MODE.signalling)
        return

    def received_disconnect(self, frame):
        self.log("DISCONNECTED...............")
        self.set_state(States.DISCONNECTED)
        self.is_ISS = False
        disconnect_ack_frame = self.frame_factory.build_p2p_connection_disconnect_ack(self.session_id)
        self.launch_twr_irs(disconnect_ack_frame, self.ENTIRE_CONNECTION_TIMEOUT, mode=FREEDV_MODE.signalling)

    def received_disconnect_ack(self, frame):
        self.log("DISCONNECTED...............")
        self.set_state(States.DISCONNECTED)


    def transmit_arq(self):
        pass
        #command = cmd_class(self.config, self.states, self.eve, params)
        #app.logger.info(f"Command {command.get_name()} running...")
        #if command.run(app.modem_events, app.service_manager.modem):

    def received_arq(self):
        pass