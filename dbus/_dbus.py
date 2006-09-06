"""Module for high-level communication over the FreeDesktop.org Bus (DBus)

DBus allows you to share and access remote objects between processes
running on the desktop, and also to access system services (such as
the print spool).

To use DBus, first get a Bus object, which provides a connection to one
of a few standard dbus-daemon instances that might be running. From the
Bus you can get a RemoteService. A service is provided by an application or
process connected to the Bus, and represents a set of objects. Once you
have a RemoteService you can get a RemoteObject that implements a specific interface
(an interface is just a standard group of member functions). Then you can call
those member functions directly.

You can think of a complete method call as looking something like::

    Bus:SESSION -> Service:org.gnome.Evolution -> Object:/org/gnome/Evolution/Inbox -> Interface: org.gnome.Evolution.MailFolder -> Method: Forward('message1', 'seth@gnome.org')

This communicates over the SESSION Bus to the org.gnome.Evolution process to call the
Forward method of the /org/gnome/Evolution/Inbox object (which provides the
org.gnome.Evolution.MailFolder interface) with two string arguments.

For example, the dbus-daemon itself provides a service and some objects::

    # Get a connection to the desktop-wide SESSION bus
    bus = dbus.Bus(dbus.Bus.TYPE_SESSION)

    # Get the service provided by the dbus-daemon named org.freedesktop.DBus
    dbus_service = bus.get_service('org.freedesktop.DBus')

    # Get a reference to the desktop bus' standard object, denoted
    # by the path /org/freedesktop/DBus. The object /org/freedesktop/DBus
    # implements the 'org.freedesktop.DBus' interface
    dbus_object = dbus_service.get_object('/org/freedesktop/DBus',
                                           'org.freedesktop.DBus')

    # One of the member functions in the org.freedesktop.DBus interface
    # is ListServices(), which provides a list of all the other services
    # registered on this bus. Call it, and print the list.
    print(dbus_object.ListServices())
"""

__all__ = ('Bus', 'SystemBus', 'SessionBus', 'StarterBus', 'Interface',
        # From exceptions (some originally from _dbus_bindings)
        'DBusException', 'ConnectionError', 'MissingErrorHandlerException',
        'MissingReplyHandlerException', 'ValidationException',
        'IntrospectionParserException', 'UnknownMethodException',
        'NameExistsException',
        # proxies, matchrules are not public API, so exclude them
        )
__docformat__ = 'reStructuredText'

import dbus
import _dbus_bindings
import weakref

from proxies import *
from exceptions import *
from matchrules import *

class Bus(object):
    """A connection to a DBus daemon.

    One of three possible standard buses, the SESSION, SYSTEM,
    or STARTER bus
    """
    TYPE_SESSION    = _dbus_bindings.BUS_SESSION
    TYPE_SYSTEM     = _dbus_bindings.BUS_SYSTEM
    TYPE_STARTER = _dbus_bindings.BUS_STARTER

    """bus_type=[Bus.TYPE_SESSION | Bus.TYPE_SYSTEM | Bus.TYPE_STARTER]
    """

    ProxyObjectClass = ProxyObject

    START_REPLY_SUCCESS = _dbus_bindings.DBUS_START_REPLY_SUCCESS
    START_REPLY_ALREADY_RUNNING = _dbus_bindings.DBUS_START_REPLY_ALREADY_RUNNING

    _shared_instances = weakref.WeakValueDictionary()

    def __new__(cls, bus_type=TYPE_SESSION, use_default_mainloop=True, private=False):
        """Constructor, returning an existing instance where appropriate.

        The returned instance is actually always an instance of `SessionBus`,
        `SystemBus` or `StarterBus`.

        :Parameters:
            `bus_type` : cls.TYPE_SESSION, cls.TYPE_SYSTEM or cls.TYPE_STARTER
                Connect to the appropriate bus
            `use_default_mainloop` : bool
                If true (default), automatically register the new connection
                to be polled by the default main loop, if any
            `private` : bool
                If true, never return an existing shared instance, but instead
                return a private connection
        """
        if (not private and bus_type in cls._shared_instances):
            return cls._shared_instances[bus_type]

        # this is a bit odd, but we create instances of the subtypes
        # so we can return the shared instances if someone tries to
        # construct one of them (otherwise we'd eg try and return an
        # instance of Bus from __new__ in SessionBus). why are there
        # three ways to construct this class? we just don't know.
        if bus_type == cls.TYPE_SESSION:
            subclass = SessionBus
        elif bus_type == cls.TYPE_SYSTEM:
            subclass = SystemBus
        elif bus_type == cls.TYPE_STARTER:
            subclass = StarterBus
        else:
            raise ValueError('invalid bus_type %s' % bus_type)

        bus = object.__new__(subclass)

        bus._bus_type = bus_type
        bus._bus_names = weakref.WeakValueDictionary()
        bus._match_rule_tree = SignalMatchTree()

        # FIXME: if you get a starter and a system/session bus connection
        # in the same process, it's the same underlying connection that
        # is returned by bus_get, but we initialise it twice
        bus._connection = _dbus_bindings.bus_get(bus_type, private)
        bus._connection.add_filter(bus._signal_func)

        if use_default_mainloop:
            func = getattr(dbus, "_dbus_mainloop_setup_function", None)
            if func:
                func(bus)

        if not private:
            cls._shared_instances[bus_type] = bus

        return bus

    def __init__(self, *args, **keywords):
        # do nothing here because this can get called multiple times on the
        # same object if __new__ returns a shared instance
        pass

    def close(self):
        """Close the connection."""
        self._connection.close()

    def get_connection(self):
        """Return the underlying `_dbus_bindings.Connection`."""
        return self._connection

    def get_session(private=False):
        """Static method that returns a connection to the session bus.
        
        :Parameters:
            `private` : bool
                If true, do not return a shared connection.
        """
        return SessionBus(private=private)

    get_session = staticmethod(get_session)

    def get_system(private=False):
        """Static method that returns a connection to the system bus.
        
        :Parameters:
            `private` : bool
                If true, do not return a shared connection.
        """
        return SystemBus(private=private)

    get_system = staticmethod(get_system)


    def get_starter(private=False):
        """Static method that returns a connection to the starter bus.

        :Parameters:
            `private` : bool
                If true, do not return a shared connection.
        """
        return StarterBus(private=private)

    get_starter = staticmethod(get_starter)


    def get_object(self, named_service, object_path):
        """Get a proxy object to call over the bus"""
        return self.ProxyObjectClass(self, named_service, object_path)

    def _create_args_dict(self, keywords):
        args_dict = None 
        for (key, value) in keywords.iteritems():
            if key.startswith('arg'):
                try:
                    snum = key[3:]
                    num = int(snum)

                    if not args_dict:
                        args_dict = {}

                    args_dict[num] = value
                except ValueError:
                    raise TypeError("Invalid arg index %s"%snum)
            elif key in ("sender_keyword", "path_keyword"):
                pass
            else:
                raise TypeError("Unknown keyword %s"%(key)) 

        return args_dict    

    def add_signal_receiver(self, handler_function, 
                                  signal_name=None,
                                  dbus_interface=None,
                                  named_service=None,
                                  path=None,
                                  **keywords):
        """Arrange for the given function to be called when a signal matching
        the parameters is emitted.

        :Parameters:
            `handler_function` : callable
                The function to be called.
            `signal_name` : str
                The signal name; None (the default) matches all names
            `dbus_interface` : str
                The D-Bus interface name with which to qualify the signal;
                None (the default) matches all interface names
            `named_service` : str
                A bus name for the sender, which will be resolved to a
                unique name if it is not already; None (the default) matches
                any sender
            `path` : str
                The object path of the object which must have emitted the
                signal; None (the default) matches any object path
            `sender_keyword` : str
                If not None (the default), the handler function will receive
                the unique name of the sending endpoint as a keyword
                argument with this name
            `path_keyword` : str
                If not None (the default), the handler function will receive
                the object-path of the sending object as a keyword argument
                with this name
            `keywords`
                If there are additional keyword parameters of the form
                ``arg``\ *n*, match only signals where the *n*\ th argument
                is the value given for that keyword parameter
        """

        args_dict = self._create_args_dict(keywords)

        if (named_service and named_service[0] != ':'):
            bus_object = self.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
            named_service = bus_object.GetNameOwner(named_service, dbus_interface='org.freedesktop.DBus')
        
        match_rule = SignalMatchRule(signal_name, dbus_interface, named_service, path)

        for kw in ("sender_keyword", "path_keyword"):
            if kw in keywords:
                setattr(match_rule, kw, keywords[kw])
            else:
                setattr(match_rule, kw, None)

        if args_dict:
            match_rule.add_args_match(args_dict)

        match_rule.add_handler(handler_function)

        self._match_rule_tree.add(match_rule)

        _dbus_bindings.bus_add_match(self._connection, repr(match_rule))

    def remove_signal_receiver(self, handler_function, 
                               signal_name=None,
                               dbus_interface=None,
                               named_service=None,
                               path=None,
                               **keywords):

        args_dict = self._create_args_dict(keywords)
    
        if (named_service and named_service[0] != ':'):
            bus_object = self.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
            named_service = bus_object.GetNameOwner(named_service, dbus_interface='org.freedesktop.DBus')
        
        match_rule = SignalMatchRule(signal_name, dbus_interface, named_service, path)

        if (args_dict):
            match_rule.add_args_match(args_dict)

        if (handler_function):
            match_rule.add_handler(handler_function)
        
        self._match_rule_tree.remove(match_rule)
        
        #TODO we leak match rules in the lower level bindings.  We need to ref count them

    def get_unix_user(self, named_service):
        """Get the unix user for the given named_service on this Bus"""
        return _dbus_bindings.bus_get_unix_user(self._connection, named_service)
    
    def _signal_func(self, connection, message):
        if (message.get_type() != _dbus_bindings.MESSAGE_TYPE_SIGNAL):
            return _dbus_bindings.HANDLER_RESULT_NOT_YET_HANDLED
        
        dbus_interface      = message.get_interface()
        named_service       = message.get_sender()
        path                = message.get_path()
        signal_name         = message.get_member()

        match_rule = SignalMatchRule(signal_name, dbus_interface, named_service, path)

        self._match_rule_tree.exec_matches(match_rule, message)

    def start_service_by_name(self, named_service):
        """Start a service which will implement the given bus name on this
        Bus.

        :Parameters:
            `named_service` : str
                The well-known bus name for which an implementation is required
        """
        return _dbus_bindings.bus_start_service_by_name(self._connection, named_service)

    def __repr__(self):
        if self._bus_type == self.TYPE_SESSION:
            name = 'SESSION'
        elif self._bus_type == self.TYPE_SYSTEM:
            name = 'SYSTEM'
        elif self._bus_type == self.TYPE_STARTER:
            name = 'STARTER'
        else:
            assert False, 'Unable to represent unknown bus type.'

        return '<dbus.Bus on %s at %#x>' % (name, id(self))
    __str__ = __repr__

class SystemBus(Bus):
    """The system-wide message bus."""
    def __new__(cls, use_default_mainloop=True, private=False):
        """Return a connection to the system bus.

        :Parameters:
            `use_default_mainloop` : bool
                If true (default), automatically register the new connection
                to be polled by the default main loop, if any
            `private` : bool
                If true, never return an existing shared instance, but instead
                return a private connection.
        """
        return Bus.__new__(cls, Bus.TYPE_SYSTEM, use_default_mainloop, private)

class SessionBus(Bus):
    """The session (current login) message bus."""
    def __new__(cls, use_default_mainloop=True, private=False):
        """Return a connection to the session bus.

        :Parameters:
            `use_default_mainloop` : bool
                If true (default), automatically register the new connection
                to be polled by the default main loop, if any
            `private` : bool
                If true, never return an existing shared instance, but instead
                return a private connection.
        """
        return Bus.__new__(cls, Bus.TYPE_SESSION, use_default_mainloop, private)

class StarterBus(Bus):
    """The bus that activated this process (only valid if
    this process was launched by DBus activation).
    """
    def __new__(cls, use_default_mainloop=True, private=False):
        """Return a connection to the bus that activated this process.

        :Parameters:
            `use_default_mainloop` : bool
                If true (default), automatically register the new connection
                to be polled by the default main loop, if any
            `private` : bool
                If true, never return an existing shared instance, but instead
                return a private connection.
        """
        return Bus.__new__(cls, Bus.TYPE_STARTER, use_default_mainloop, private)

class Interface:
    """An interface into a remote object.

    An Interface can be used to wrap ProxyObjects
    so that calls can be routed to their correct
    dbus interface
    """

    def __init__(self, object, dbus_interface):
        """Construct a proxy for the given interface on the given object.

        :Parameters:
            `object` : `dbus.proxies.ProxyObject`
                The remote object
            `dbus_interface` : str
                An interface the `object` implements
        """
        self._obj = object
        self._dbus_interface = dbus_interface

    def connect_to_signal(self, signal_name, handler_function, dbus_interface = None, **keywords):
        """Arrange for a function to be called when the given signal is
        emitted.

        :Parameters:
            `signal_name` : str
                The name of the signal
            `handler_function` : callable
                A function to be called (FIXME arguments?) when the signal
                is emitted by the remote object.
            `dbus_interface` : str
                Optional interface with which to qualify the signal name.
                The default is to use the interface this Interface represents.
            `sender_keyword` : str
                If not None (the default), the handler function will receive
                the unique name of the sending endpoint as a keyword
                argument with this name
            `path_keyword` : str
                If not None (the default), the handler function will receive
                the object-path of the sending object as a keyword argument
                with this name
            `keywords`
                If there are additional keyword parameters of the form
                ``arg``\ *n*, match only signals where the *n*\ th argument
                is the value given for that keyword parameter
        """
        if not dbus_interface:
            dbus_interface = self._dbus_interface
            
        self._obj.connect_to_signal(signal_name, handler_function, dbus_interface, **keywords)

    def __getattr__(self, member, **keywords):
        # FIXME: this syntax is bizarre.
        if (keywords.has_key('dbus_interface')):
            _dbus_interface = keywords['dbus_interface']
        else:
            _dbus_interface = self._dbus_interface

        if member == '__call__':
            return object.__call__
        else:
            ret = self._obj.__getattr__(member, dbus_interface=_dbus_interface)
            return ret

    def __repr__(self):
        return '<Interface %r implementing %r at %#x>'%(
        self._obj, self._dbus_interface, id(self))
    __str__ = __repr__
