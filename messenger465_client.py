#!/usr/bin/env python3
import sys
import tkinter
import socket
import argparse

from select import select


__author__ = "jsommers@colgate.edu"
__doc__ = '''
A simple model-view controller-based message board/chat client application.
https://docs.google.com/document/d/1NTVX_DYuiX7z_l1kdyg7lVjHmY1T59a0MPRGLPiAKqE/edit?usp=sharing
'''
if sys.version_info[0] != 3:
    print ("This code must be run with a python3 interpreter!")
    sys.exit()


def chunks(l, n):
    """
    Yield successive n-sized chunks from l.

    from http://stackoverflow.com/a/312464
    """
    for i in range(0, len(l), n):
        yield l[i:i+n]


class BaseMessageBoardException(Exception):
    pass


class ServerException(BaseMessageBoardException):
    '''
    Raised when the server has a problem and sends an error
    '''

    def __init__(self, server_error):
        self.server_error = server_error

    def __str__(self):
        return 'Server error: ' + self.server_error


class UnknownResponse(BaseMessageBoardException):
    '''
    Raised when the response from the server can not be interpreted
    '''
    def __init__(self, response):
        self.response = response

    def __str__(self):
        return 'Unkown server response: ' + self.response


class Timeout(BaseMessageBoardException):
    '''
    Raised when the server did not response before the timeout
    '''
    def __init__(self):
        pass

    def __str__(self):
        return 'Server timeout'


class MessageBoardNetwork(object):
    '''
    Model class in the MVC pattern.  This class handles
    the low-level network interactions with the server.
    It should make GET requests and POST requests (via the
    respective methods, below) and return the message or
    response data back to the MessageBoardController class.
    '''

    BUFFER_LENGTH = 1400
    HEADER = 'A'
    TIMEOUT = 0.1  # 100ms
    MAX_USERNAME_LENGTH = 8
    MAX_MESSAGE_LENGTH = 60

    def __init__(self, host, port):
        '''
        Constructor. You should create a new socket
        here and do any other initialization.
        '''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.host = host
        self.port = port

    @property
    def address(self):
        return (self.host, self.port)

    def get_messages(self):
        '''
        You should make calls to get messages from the message
        board server here.
        '''

        response = self._communicate_with_validation('GET')
        if response:
            for (user, timestamp, message) in chunks(response.split('::'), 3):
                yield '{} {} {}'.format(user, timestamp, message)

    def post_message(self, user, message):
        '''
        You should make calls to post messages to the message
        board server here.
        '''
        request = 'POST {user} :: {message}'.format(user=user, message=message)
        self._communicate_with_validation(request)

    def _communicate_with_validation(self, data):
        '''
        Talk to the server and make sure the response starts with OK
        '''
        return self._validate_server_response(self._communicate(data))

    @classmethod
    def _validate_server_response(self, data):
        '''
        Takes the app layer data returned by the server and validates
        on the first word. On OK it will return the rest of the data,
        on ERROR it will raise a ServerException and if the first word
        is neither it will raise an UnkownResponse
        '''
        # have to do this weird assignment so that all these string are resolved:
        # `OK`, `OK <other text`, ``, `sdfs`.
        status, *message = data.split(' ', 1)
        message = ''.join(message)
        if status == 'OK':
            return message
        if status == 'ERROR':
            raise ServerException(message)
        raise UnknownResponse(data)

    def _communicate(self, data):
        '''
        Sends some data to the server and returns the response
        '''
        return self._parse_recieved_data(
            self._send_on_socket(
                self._prepare_data_for_sending(data)
            )
        )

    def _send_on_socket(self, data):
        '''
        This will do the actual business of sending some data to the server
        and returning the resault (with timeouts).

        Will send the data as is, append appropriate headers beforehand.
        '''
        self.socket.sendto(data, self.address)

        # wait on the socket to return within the timeout
        try:
            # if it does, the first tuple will have a value in it, if not it
            # won't so the unpacking will fail and a ValueError will be raised
            (_,), _, _ = select([self.socket], [], [], self.TIMEOUT)
        except ValueError:
            raise Timeout()
        network_message, address = self.socket.recvfrom(self.BUFFER_LENGTH)
        return network_message

    @classmethod
    def _prepare_data_for_sending(cls, data):
        '''
        Takes the app layer data and adds the app layer header to it, to prepare
        it to be sent to the server
        '''
        return (cls.HEADER + data).encode()

    @classmethod
    def _parse_recieved_data(cls, network_message):
        '''
        Makes sure that the app layer header returned by the server is correct
        and returns the app layer data
        '''
        network_message_string = network_message.decode()
        if not network_message_string.startswith(cls.HEADER):
            UnknownResponse("Doesn't start with header: {}".format(network_message_string))
        return network_message_string[1:]


class MessageBoardController(object):
    '''
    Controller class in MVC pattern that coordinates
    actions in the GUI with sending/retrieving information
    to/from the server via the MessageBoardNetwork class.
    '''

    def __init__(self, myname, host, port):

        self.name = myname
        self.view = MessageBoardView(myname)
        self.view.setMessageCallback(self.post_message_callback)
        self.net = MessageBoardNetwork(host, port)

        self.post_status = ''
        self.retrieve_status = ''
        self._set_statuses()

    def run(self):
        self.view.after(1000, self.retrieve_messages)
        self.view.mainloop()

    def post_message_callback(self, m):
        '''
        This method gets called in response to a user typing in
        a message to send from the GUI.  It should dispatch
        the message to the MessageBoardNetwork class via the
        postMessage method.
        '''
        self._set_post_status('Posting message...')
        try:
            self.net.post_message(self.name, m)
        except BaseMessageBoardException as e:
            self._set_post_status('Posting error: {}'.format(e))
        else:
            self._set_post_status('')

    def retrieve_messages(self):
        '''
        This method gets called every second for retrieving
        messages from the server.  It calls the MessageBoardNetwork
        method getMessages() to do the "hard" work of retrieving
        the messages from the server, then it should call
        methods in MessageBoardView to display them in the GUI.

        You'll need to parse the response data from the server
        and figure out what should be displayed.

        Two relevant methods are (1) self.view.setListItems, which
        takes a list of strings as input, and displays that
        list of strings in the GUI, and (2) self.view.setStatus,
        which can be used to display any useful status information
        at the bottom of the GUI.
        '''
        self.view.after(1000, self.retrieve_messages)

        self._set_retrieve_status('Retrieving messages...')
        try:
            messages = list(self.net.get_messages())
        except BaseMessageBoardException as e:
            self._set_retrieve_status('Retrieving error: {}'.format(e))
        else:
            self.view.setListItems(messages)
            self._set_retrieve_status('Retrieved {} mesages'.format(len(messages)))

    def _set_post_status(self, status):
        '''
        Set the posting part of the status message
        '''
        self.post_status = status
        self._set_statuses()

    def _set_retrieve_status(self, status):
        '''
        Set the retrieving part of the status message
        '''
        self.retrieve_status = status
        self._set_statuses()

    def _set_statuses(self):
        '''
        Joing the `retrieve_status` and `post_status`'s together into one string
        seperated by a slash and tell the view to set the status to it.
        '''
        status = ' / '.join(filter(None, [self.retrieve_status, self.post_status]))
        self.view.setStatus(status)


class MessageBoardView(tkinter.Frame):
    '''
    The main graphical frame that wraps up the chat app view.
    This class is completely written for you --- you do not
    need to modify the below code.
    '''
    def __init__(self, name):
        self.root = tkinter.Tk()
        tkinter.Frame.__init__(self, self.root)
        self.root.title('{} @ messenger465'.format(name))
        self.width = 80
        self.max_messages = 20
        self._createWidgets()
        self.pack()

    def _createWidgets(self):
        self.message_list = tkinter.Listbox(self, width=self.width, height=self.max_messages)
        self.message_list.pack(anchor="n")

        self.entrystatus = tkinter.Frame(self, width=self.width, height=2)
        self.entrystatus.pack(anchor="s")

        self.entry = tkinter.Entry(self.entrystatus, width=self.width)
        self.entry.grid(row=0, column=1)
        self.entry.bind('<KeyPress-Return>', self.newMessage)

        self.status = tkinter.Label(self.entrystatus, width=self.width, text="starting up")
        self.status.grid(row=1, column=1)

        self.quit = tkinter.Button(self.entrystatus, text="Quit", command=self.quit)
        self.quit.grid(row=1, column=0)

    def setMessageCallback(self, messagefn):
        '''
        Set up the callback function when a message is generated
        from the GUI.
        '''
        self.message_callback = messagefn

    def setListItems(self, mlist):
        '''
        mlist is a list of messages (strings) to display in the
        window.  This method simply replaces the list currently
        drawn, with the given list.
        '''
        self.message_list.delete(0, self.message_list.size())
        self.message_list.insert(0, *mlist)

    def newMessage(self, evt):
        '''Called when user hits entry in message window.  Send message
        to controller, and clear out the entry'''
        message = self.entry.get()
        if len(message):
            self.message_callback(message)
        self.entry.delete(0, len(self.entry.get()))

    def setStatus(self, message):
        '''Set the status message in the window'''
        self.status['text'] = message

    def end(self):
        '''Callback when window is being destroyed'''
        self.root.mainloop()
        try:
            self.root.destroy()
        except:
            pass

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='COSC465 Message Board Client')
    parser.add_argument('--host', dest='host', type=str, default='localhost',
                        help='Set the host name for server to send requests to (default: localhost)')
    parser.add_argument('--port', dest='port', type=int, default=1111,
                        help='Set the port number for the server (default: 1111)')
    parser.add_argument('--username', dest='username', type=str,
                        help='Set your user name (max 8 characters')
    args = parser.parse_args()

    app = MessageBoardController(args.username, args.host, args.port)
    app.run()
