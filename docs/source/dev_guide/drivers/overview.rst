.. include:: ../../substitutions.sub

.. _dev-driv-overview:

Writing a driver
================

This section will focus on giving you a quick overview of the tools available
to you to write your driver. While it should be sufficient to write simple
drivers you may want to check the following sections for more detailed
explanations.

.. note::

    It may seem obvious, but, in order to write a driver for your instrument
    you need both a good knowledge of the instrument and to read its manual.
    Finally you need to have access to the real instrument as the manual is
    likely to be elliptic if not incorrect in some cases (and it is perfectly
    possible for your instrument firmware to be buggy). Finally in the early
    stages of development you should make sure you can communicate with your
    instrument using a third party tool such as NiMAX for VISA instruments or
    the vendor provided software in other cases.

.. contents::

General organization
--------------------

I3py drivers are organized along the following concepts:

- the "driver" is at the highest level, it is responsible for handling the
  communication with the physical instrument.
- the parameters of the instrument that can be read and possibly set by the
  user, and whose value does not change spontaneously (any measured quantity
  typically falls outside this category) are described using "features", which
  are advanced and highly customizable descriptors (ie properties, please refer
  to Python documentation if you do not know what a property is).
- the operations that an instrument can perform (such as a measure), are
  described using an "action" that is a simple wrapper around a method. It
  provides optionally some validation/conversion of the argument and return
  values.
- finally drivers can be structured in "subsystems" and multiple channels or
  cards inside a rack can be described using a "channel", which is nothing else
  than a subsystem with an attached id.

All the above concepts will be illustrated below on concrete examples.

Creating the driver
-------------------

In I3py, each driver is defined in a class declaration. All drivers should
inherit from the |BaseDriver| class, however most of the time you will most
probably use a derived class handling the low-level communication with the
instrument such as |VisaMessageDriver|.

As I3py strives for uniformity in the drivers, it provides for some instruments
a standardized base class defining the expected features and actions. As those
'standards' cannot assume any communication mean with the instrument, to use
those your driver should inherit from a base class handling the communication
and all the 'standards' your instrument supports.

.. code-block:: python

    class MyDriver(VisaMessageDriver, IEEEIdentify):
        """My driver (supporting *IDN?) docstring.

        """
        pass

If no base class provides the proper communication method to read and write the
values of the instrument features, you will have to implement the following
methods:

    - |HasFeatures.default_get_feature|: This method is charged with querying
      the value of the feature.
      See the API docs for more details.
    - |HasFeatures.default_set_feature|: This method is charged with setting
      the value of the feature.
      See the API docs for more details.
    - |HasFeatures.default_check_operation|: This method is charged with
      checking that setting a feature did go properly. This method is free to
      use any method it see fit to perform this check.
      See the API docs for more details.

For more details about what are standards and how to use them please refer to
:ref:`dev-driv-standards`

.. note::

    To simplify the handling of changes to driver over time I3py recommend to
    add a class variable `__version__` to all drivers. The format of this
    variable should be the one of a usual version string:
    MAJOR.MINOR.MICRO

Adding a Feature
----------------

A Feature describes a property of the instrument, that, as already mentioned
does not change in a spontaneous way. This restriction comes from the fact that
the values of features are cached. They can and should be discarded when some
other setting of the driver is modified, but not in a spontaneous manner.

To a add a Feature to your instrument you have nothing else to do that assign
a Feature subclass to an identifier. As illustrated in the example below :

.. code-block:: python

    class MyDriver(VisaMessageDriver, IEEEIdentify):
        """My driver (supporting *IDN?) docstring.

        """
        mode = Unicode('MODE?', 'MODE {}', values=('CW', 'PULSED'))

The first argument is the command to get the value of the feature, the second
the command to set it. For message based VISA driver, this is the true SCPI
command string and the braces will be filled with the set value.

Additional keywords are used to customized the action taken before
getting/setting a value (such as checking this is allowed), how to extract
the value or how to validate that the value is meaningful for the instrument.

When subclassing an existing instrument it is often possible that a feature
already exists on the parent class but is not properly configured (for example
the values are incorrect). In such cases, it is not necessary to entirely
redefine the feature, one can use |set_feat| to change the proper keyword
arguments values.

.. code-block:: python

    class MyNewDriver(MyDriver):
        """My driver (supporting *IDN?) docstring.

        """
        mode = set_feat(values=('CW', 'PULSED', 'TRIGGERED'))

The detailed working of Features is detailed in :ref:`dev-driv-features`, and
all the existing  features are described in the API. Finally, as instruments
can be often quite surprising in their behaviors, the default behaviors of the
provided features  may prove insufficient. More complex customization are
possible and detailed in the section :ref:`dev-driv-advanced` of this manual.

Adding an Action
----------------

Actions are light wrapper around methods. They provide similar facility to run
checks and conversion on the input and output values as do features. To declare
one, you only have to declare a method:

.. code-block:: python

    class MyDriver(VisaMessageDriver):
        """My driver (suppporting *IDN?) docstring.

        """

        @Action(values={'kind': ('volt', 'curr')})
        def read_state(self, kind):
            """Read the instrument state.

            """
            pass

The above example shows how to check the value of an argument is valid.

The detailed working of actions is described in :ref:`dev-driv-actions` section.
Just like  features several classes of actions exist and are describe in the
API. Actions support advanced customization just like features which are
described in section :ref:`dev-driv-advanced`

Using subsystem and channels
----------------------------

Subsystems allow to group features into coherent ensemble, which can allow to
avoid ridiculously long names. For example many lock-in amplifiers include a
built-in oscillator and subsytems allow for example to group the related
features such as amplitude and frequency as shown below:

.. code-block:: python

    class MyDriver(VisaMessageDriver):
        """My driver (supporting *IDN?) docstring.

        """

        oscillator = subsystem()
        with oscillator as o:

            o.frequency = Float('OSC:FREQ?', 'OSC:FREQ {}')

Actions can also be attached to a subsystems:

.. code-block:: python

    class MyDriver(VisaMessageDriver):
        """My driver (supporting *IDN?) docstring.

        """

        oscillator = subsystem()
        with oscillator as o:

            @o
            @Action()
            def is_sync(self):
                pass

By default, a subsystem is a subclass of || and any subsystem of the parent
class of the driver. You can specify additional base classes as a tuple passed
as first argument to subsystem.

Channels are similar to subsytems but are identified by an id as an instrument
may have an arbitrary number of channel of the same kind. Adding a channel to
an instrument is similar to adding a subsystem save that one must specify
what are the valid channel ids. One can specify a static list of ids or a the
name of a method on the parent listing the available channel when called. This
method should take no argument. Furthermore one can declare, aliases for the
channel ids to provide more user friendly name than the ones used by the
driver.

For more details please refer to the API documentation or to the dedicated
section of the documentation about subsystems and channels
:ref:`dev-driv-subsystem`.

Handling options
----------------

Depending on the instrument firmware or the option bought, some capabilities of
the instrument may not be available. To reflect this reality, i3py allows to
define special features |Options| used to recover the instrument options.

.. note::

	A single driver can define multiple options features but they all use
	different names.

Features, actions, subsystem and channel all support a dedicated keyword
argument 'options' to specify tests to perform on the instrument option before
granting the user access to it for the first time. The full check is only
performed the first time since options are meant to describe hardware or
firmware settings that cannot change during the instrument operation. The
format in which to specify the checks is the following:

	'feature_options_name['option_name'] == option_value'

Actually any valid boolean assertion can be evaluated so if an option can only
be True or False the equality test is useless. Furthermore multiple test can be
separated by ; .

.. note::

	Operation that cannot be performed at runtime because the instrument is not
	properly configured fall outside the scope of options and should be
	inhibited if necessary using the 'checks' mechanism that exists on
	features, actions, subsystems and channels.

For more details please refer to the API documentation.

Special class variables for VISA based driver
---------------------------------------------

In the case of VISA based drivers, it is desirable to specify which
communication interfaces are supported by the instrument, along which the
parameters to use (such as termination characters, which may differ between
interfaces). All those informations can be specified to I3py drivers through
the use of the class level variables listed below:

INTERFACES
^^^^^^^^^^

Dictionary specifying the interfaces supported by the instrument. For each
type of interface a dictionary (or a list of dictionary), specifying the
default arguments to use should be provided. Valid interfaces are :

+ ASRL: serial interface (RS232)
+ USB: usb interface
+ TCPIP: ethernet based interface
+ GPIB: gpib based interface
+ PXI: pxi based interface
+ VXI: vxi based interface

For each supported interface, the dictionary should contain at least the
resource class to use. In addition, it can contain interface specific
settings that users will not have to provide to start the driver. For
example, if the instrument support the using raw sockets on TCPIP, the port
number is required and can be specified as follow.

.. code-block:: python

INTERFACES = {'TCPIP': {'resource_class': 'SOCKET',
                       'port': '50000'}}

The valid keys for each interface matches the named used in VISA resource
names which are described in PyVISA documentation_.

.. _documentation: https://pyvisa.readthedocs.io/en/stable/names.html

DEFAULTS
^^^^^^^^

Dictionary specifying the default parameters to use for the VISA session.
As some of those can be interface or resource specific, the valid keys for the dictionary include any pair (interface_type, resource_class), any
interface_type, any resource_class and `'COMMON'` that applies
to all interfaces/resources. The values associated to each key is expected to
be a dictionary, whose keys match the attributes of the underlying VISA
resource. The most commons are:

- write_termination: character appended at the end of each sent message
- read_termination: character expected at the end of each received message.
- timeout: time in ms after which to consider that the communication failed.


NON_VISA_NAMES
^^^^^^^^^^^^^^

By default all arguments passed to a VISA driver are used to build the
resource name. This class hold a tuple of named reserved to other usage.
By default it is set to `('parameters', 'backend')`, which should be
sufficient be sufficient in most cases.

'parameters' is a dictionary whose content is by default passed to the
underlying PyVISA object, but it is a matter of simply overriding initialize
to handle it in a different fashion.
