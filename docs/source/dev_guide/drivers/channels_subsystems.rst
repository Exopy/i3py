.. include:: ../../substitutions.sub

.. _dev-driv-subsystem:

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
syntax as already mentioned in :ref:`dev-driv-overview`.

.. code-block:: python

    class MyDriver(VisaMessageDriver):
        """My driver with a subsystem.

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

As mentioned in the introduction, subsystems can define tests (options and
checks) that apply to all their features and actions. Those can be declared
just like for features and actions by passing strings defining the options
('options' argument) and checks ('checks' argument).

The options will be tested when one try to access the subsystem from the
driver:

.. code-block:: python

    ss = driver.subsystem

If the tests do not evaluate to true, an :py:exc:`AttributeError` will be
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

Features working in subsystems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order for features to work in subsystems, subsystems implement:
|HasFeatures.default_get_feature|, |HasFeatures.default_set_feature|,
|HasFeatures.default_check_operation|. As a subsystem is nothing but a
container, it simply propagate the call to its parent, without altering the
arguments.

Channels
--------

In several respects, channels are very similar to subsystems. Just as them,
they follow mostly the same logic as far as subclassing is concerned and
also support checks and options which work in the same way. The key
difference between subsystems and channels is that where only one subsystem
is instantiated per driver, multiple instances of a channel can be tied to
the same driver. The following section will describe the differences
between channels and subsystems.

Declaration
^^^^^^^^^^^

Channels are declared in the body of a driver using the following
syntax as already hinted in :ref:`dev-driv-overview`. The key difference with
a subsystem is that a way to identify the valid channels id is generally
required as first argument.

.. code-block:: python

    class MyDriver(VisaMessageDriver):
        """My driver with a channel.

        """

        channels = channel((1, 2, 3),
                           aliases={1: ('A', 'a'), 2: 'B', 3: 'C'})
        with channels as c:

            c.frequency = Float('CH{ch_id}:FREQ?', 'OSC:FREQ {}')

            @c
            @Action()
            def is_sync(self):
                pass

The valid ids for channel can be declared as above as a tuple or
list, which make sense when the number of channel is hardcoded in the
device. Alternatively, one can pass the name of a method existing on the
parent whose signature should be (self) -> Iterable.

In some cases, it may be handy to provide alternate names for channels for
the sake of clarity. One can do so by declaring aliases. Aliases should be
a dictionary whose keys match the ids of the channels and whose values are
the allowed alternatives. Alternatives can be specified either as a simple
value or as a list/tuple.

When subclassing a driver which has channels, if no channels ids are
provided the method used on the parent driver will be inherited, and the
aliases mapping will be updated with any new value provided (note that this
will use the provided dict to update the inherited one such that duplicate
keys will be overridden).

.. note::

    As for subsystems one can specify base classes for a channel and the
    same inheritance rules apply.

Usage
^^^^^

As explained in the user guide, channel instances can be accessed using the
following syntax:

.. code-block:: python

    driver.channels[ch_id]

where `ch_id` would 1, 2, 3 or any of their aliases in the previous case.

To achieve this and allow to check for options too, the channel machinery
uses, like subsystems, a descriptor to protect the access to the object
storing the channel instances, which we will refer to as the channel
container. To make things clear, when writing:

.. code-block:: python

    c = driver.channels

c is the channel container returned by the descriptor. In addition to
supporting subscription, the container is iterable and has the following
attributes:

- available: list of the ids of the channels that can be accessed.
- aliases: mapping between the declared aliases and the matching channel
  id.

By default, the framework will use |ChannelDescriptor| for the
descriptor and |ChannelContainer| for the channel container. Just like for
subsystems, it is possible to substitute to those classes custom ones using
the `descriptor_type` and the `container_type` keyword arguments. The
substitution classes should inherit from the proper abstract classes:
|AbstractChannelDescriptor| and |AbstractChannelContainer| respectively.

Features working in channels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order for features to work in channels, channels implement:
|HasFeatures.default_get_feature|, |HasFeatures.default_set_feature|,
|HasFeatures.default_check_operation|. In the case of the first two
methods, a channel add its id under the keyword argument `ch_id` to the
keyword arguments and propagate the call the parent driver. For the third
method the call is simply forwarded on the parent.

The default behaviour is well fitted for VISA message based instruments when
the channel id is part of the command as in this case things work out the
box. The user simply has to indicate where to format the channel id, as
illustrated in the above example. For instrument that requires first the
channel to be selected, it is simply a matter of overriding the method
to prepend the channel selection command.
