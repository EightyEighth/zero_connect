import zmq.green as zmq
from typing import Protocol, runtime_checkable, Final, Any
from loguru import logger


TCP: Final = "tcp"
INPROC: Final = "inproc"

PROTOCOLS: Final = [TCP, INPROC]


@runtime_checkable
class BaseTransport(Protocol):

    def request(
            self, host: str, port: int,  data: bytes, protocol: PROTOCOLS = TCP
    ) -> bytes:
        """
        Send request to the remote endpoint. Low level method.
        Uses by client for making requests.

        :arg data: data to send
        :arg host: host to send
        :arg port: port to send
        :arg protocol: protocol to use
        """
        ...

    def dispatch(
        self, host: str, port: int, topic: str, data: bytes,
        protocol: PROTOCOLS = TCP, through_broker: bool = False
    ) -> None:
        """
        Dispatch event to the remote endpoint. Low level method.
        Uses by client for dispatching events.

        :arg topic: topic to dispatch
        :arg data: data to dispatch
        :arg host: host to dispatch
        :arg port: port to dispatch
        :arg protocol: protocol to use
        :arg through_broker: use broker or not
        """
        ...

    @staticmethod
    def send(
        data: bytes, protocol: PROTOCOLS = TCP, host: str | None = None,
        port: int | None = None, socket: Any = None
    ) -> Any:
        """
        Send data to the remote endpoint. Low level method.
        Uses by server for sending responses.

        :arg data: data to send
        :arg host: host to send
        :arg port: port to send
        :arg protocol: protocol to use
        :arg socket: socket to use
        """
        ...

    @staticmethod
    def receive(socket: Any) -> bytes:
        """
        Receive data from the remote endpoint. Low level method.
        Uses by server for receiving requests.
        """
        ...


class ZeroMQTransport(BaseTransport):
    REQUEST_TIMEOUT: Final = 2500
    REQUEST_RETRIES: Final = 3
    WAIT_TIME: Final = 100

    """
    Base class for all transports. It just sent and receive data.
    """
    def __init__(self, is_debug: bool = False) -> None:
        self._context = zmq.Context()
        self._pub_event_socket = None
        self._request_socket = None
        self._is_debug = is_debug

    def request(
            self, host: str, port: int,  data: bytes, protocol: PROTOCOLS = TCP
    ) -> bytes:
        """
        Send request to the remote endpoint. Low level method.
        :param host: host to send
        :param port: port to send
        :param data: request data
        :param protocol: type of protocol
        :return: Optional[bytes]
        """

        if not self._request_socket:
            self._request_socket = self._context.socket(zmq.REQ)
            self._request_socket.connect(f"{protocol}://{host}:{port}")

        self._request_socket.send(data)
        message = self._request_socket.recv()
        logger.info(f"Response received: {message}")

        return message

    def dispatch(
            self, host: str, port: int, topic: str, data: bytes,
            protocol: PROTOCOLS = TCP, through_broker: bool = False
    ) -> None:
        if not self._pub_event_socket:
            self._pub_event_socket = self._context.socket(zmq.PUB)
            if through_broker:
                self._pub_event_socket.connect(f"{protocol}://{host}:{port}")
            else:
                self._pub_event_socket.bind(f"{protocol}://{host}:{port}")

        data = [topic.encode(), data]
        logger.info(f"Message {data} published to topic: {topic.encode()}")
        self._pub_event_socket.send_multipart(data)

    @staticmethod
    def send(
        data: bytes, protocol: PROTOCOLS = TCP,
        host: str = None, port: int = None, socket: zmq.Socket = None
    ) -> zmq.Socket:

        assert (host and port) or socket, "Host or socket should be defined"

        if not socket:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect(f"{protocol}://{host}:{port}")

        socket.send(data)

        return socket

    @staticmethod
    def receive(socket: zmq.Socket) -> bytes:
        result = socket.recv()

        return result
