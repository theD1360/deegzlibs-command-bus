"""Exceptions for command-bus control flow."""


class ReleaseMessage(Exception):
    """
    Skip ack/dequeue for the current message.

    Raise from a handler or middleware so ``work()`` leaves the message pending.
    Adapters that support visibility timeout (SQS, File, Redis Streams) will make
    it available again after the timeout. Omitting ``call_next`` without raising
    still acks (intentional drop).
    """
