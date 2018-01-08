.. _dev_driv_subsystem

.. include:: ../substitutions.sub

Subsystems and channels
=======================

Complex instruments usually have too many capabilities to fit reasonably in a 
single namespace, which is why SCPI commands usually define a hierarchy.
Furthermore, either because the instrument is made of multiple parts or because
the notion is built-in the instrument, another recurrent notion is the one of 
channel. Channels are usually identified by an id and share their capabilities.
To handle those two cases I3py uses the notions of "subsystems" and "channels".
As channels inherit a number of capabilities from subsystems, we will first 
describe them before moving on to the specificities of channels.

Subsystems
----------

Subsystems act mainly as container and provide little capabilities by 
themselves. They do however allow to group options and checks for all their
features and actions. The next following two sections focus on their 
declaration and on the working principle of options and checks.

    Declaration
    ^^^^^^^^^^^
    
    Subsystems can be declared in the body of a driver using the following 
    syntax as already mentioned in :ref:dev_driv_overview.
    
    .. codeblock::

        class MyDriver(VisaMessageDriver):
            """My driver (suppporting *IDN?) docstring.

            """

            oscillator = subsystem()
            with oscillator as o:

                o.frequency = Float('OSC:FREQ?', 'OSC:FREQ {}')
                
                @o
                @Action()
                def is_sync(self):
                    pass
                
    Once created, the use of a context manager allows for the use of short 
    names but also some additional magic and it should hence be used.
    
    While convenient, this syntax can be cumbersome if one needs to declare 
    nested subsystems/channels and as presented here would lead to large amount
    of code duplication for similar instruments. To allow the declaration of 
    subsystems outside of a driver declaration, |subsystem| supports to be 
    passed a list of base classes as first argument ('bases'). Those base
    classes do not have to be subsystems themselves (subclass of 
    |AbstractSubSystem|) and if none of them are, a proper class will be added
    by the framework.
    
    When subclassing a driver which has subsystems, one can modify the 
    subsystems (adding/modifying actions/features) by simply redeclaring it 
    with the same name and proceeding as for a new one. The framework will 
    identify that the subsystem already exists and will use the version present
    on the base class as base class for the subsystem. 
    
    .. note::
        
        In the case of multiple inheritance, if several of the driver base 
        classes declare the same subsystem, the framework will use the one
        present on the first class of the mro. Other classes can be added as 
        arguments.

    Options and checks
    ^^^^^^^^^^^^^^^^^^
    
    As mentioned in introduction, subsystems can define tests (options and 
    checks) that apply to all their features and actions. Those can be declared 
    just like for features and actions by passing strings defining the options
    ('options' argument) and checks ('checks' argument).
    
    The options will be tested when one try to access the subsystem from the 
    driver::
    
        ss = driver.subsystem

    If the tests do not evaluate to true, an :py:exc:`AttributeError``will be 
    raised mimicking a missing attribute. And as for all other options test the 
    result will be cached. To implement this, the subsystem is accessed through
    a descriptor.
    
    .. note::
        
        By default, the framework uses |SubSystemDescriptor| as descriptor to 
        protect the access to a subsystem. You can specify an alternative 
        descriptor using the 'descriptor' argument of subsystem. Alternative 
        descriptor should inherit from |AbstractSubSystemDescriptor|.
        
    Checks on the other hand are run each time a feature is accessed or an 
    action is run. To achieve this, the framework customize the 
    features/actions of the subsystem by adding an 'enabling' step to 
    pre_get/set/call.
    
    .. note::
        
        When a inheriting a subsystem from a parent driver, the options and 
        checks defined in the subsystem call are appended to the ones existing
        on the subsystem of the parent driver.

Channels
--------

    Declaration
    ^^^^^^^^^^^

    Usage
    ^^^^^


