from typing import Any, Dict, List

from vnpy.event import Event
from vnpy.rpc import RpcClient
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import (
    SubscribeRequest,
    HistoryRequest,
    CancelRequest,
    OrderRequest,
)
from vnpy.trader.constant import Exchange
from vnpy.trader.object import (
    BarData,
    ContractData,
    AccountData,
    PositionData,
    OrderData,
    TradeData,
)


class RpcGateway(BaseGateway):
    """
    The interface that VeighNa uses to connect to the rpc service.
    """

    default_name: str = "RPC"

    default_setting: Dict[str, str] = {
        "Request address": "tcp://127.0.0.1:2014",
        "Subscription address": "tcp://127.0.0.1:4102",
    }

    exchanges: List[Exchange] = list(Exchange)

    def __init__(self, event_engine, gateway_name: str) -> None:
        """Constructor"""
        super().__init__(event_engine, gateway_name)

        self.symbol_gateway_map: Dict[str, str] = {}

        self.client: "RpcClient" = RpcClient()
        self.client.callback = self.client_callback

    def connect(self, setting: dict) -> None:
        """Connect trading interface"""
        req_address: str = setting["Request address"]
        pub_address: str = setting["Subscription address"]

        self.client.subscribe_topic("")
        self.client.start(req_address, pub_address)

        self.write_log("Server connection successful, starting initialization query")

        self.query_all()

    def subscribe(self, req: SubscribeRequest) -> None:
        """Subscribe to Quotes"""
        gateway_name: str = self.symbol_gateway_map.get(req.vt_symbol, "")
        self.client.subscribe(req, gateway_name)

    def send_order(self, req: OrderRequest) -> str:
        """Place an order"""
        gateway_name: str = self.symbol_gateway_map.get(req.vt_symbol, "")
        gateway_orderid: str = self.client.send_order(req, gateway_name)

        if gateway_orderid:
            _, orderid = gateway_orderid.split(".")
            return f"{self.gateway_name}.{orderid}"
        else:
            return gateway_orderid

    def cancel_order(self, req: CancelRequest) -> None:
        """Order cancellation"""
        gateway_name: str = self.symbol_gateway_map.get(req.vt_symbol, "")
        self.client.cancel_order(req, gateway_name)

    def query_account(self) -> None:
        """Inquiry funds"""
        pass

    def query_position(self) -> None:
        """Check position"""
        pass

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """Query historical data"""
        gateway_name: str = self.symbol_gateway_map.get(req.vt_symbol, "")
        return self.client.query_history(req, gateway_name)

    def query_all(self) -> None:
        """Search for basic information"""
        contracts: List[ContractData] = self.client.get_all_contracts()
        for contract in contracts:
            self.symbol_gateway_map[contract.vt_symbol] = contract.gateway_name
            contract.gateway_name = self.gateway_name
            self.on_contract(contract)
        self.write_log("Successful contract information inquiry")

        accounts: List[AccountData] = self.client.get_all_accounts()
        for account in accounts:
            account.gateway_name = self.gateway_name
            account.__post_init__()
            self.on_account(account)
        self.write_log("Funding information query successful")

        positions: List[PositionData] = self.client.get_all_positions()
        for position in positions:
            position.gateway_name = self.gateway_name
            position.__post_init__()
            self.on_position(position)
        self.write_log("Position information query successful")

        orders: List[OrderData] = self.client.get_all_orders()
        for order in orders:
            order.gateway_name = self.gateway_name
            order.__post_init__()
            self.on_order(order)
        self.write_log("Order information query successful")

        trades: List[TradeData] = self.client.get_all_trades()
        for trade in trades:
            trade.gateway_name = self.gateway_name
            trade.__post_init__()
            self.on_trade(trade)
        self.write_log("Successful trade information query")

    def close(self) -> None:
        """Close connection"""
        self.client.stop()
        self.client.join()

    def client_callback(self, topic: str, event: Event) -> None:
        """Callback function"""
        if event is None:
            print("none event", topic, event)
            return

        data: Any = event.data

        if hasattr(data, "gateway_name"):
            data.gateway_name = self.gateway_name

        if isinstance(data, (PositionData, AccountData, OrderData, TradeData)):
            data.__post_init__()

        self.event_engine.put(event)
