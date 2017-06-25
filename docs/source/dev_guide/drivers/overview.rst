.. _dev_driv_overview

.. include:: ../substitutions.sub

Writing a driver
================

This section will focus on giving you a quick overview of the tools available 
to you to write your driver. While it should be sufficient to write simple 
drivers you may want to check the following sections for more detailed 
explanations.

.. notes::

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
  user, and whose value does not change spontaneouly (any measured quantity
  typically falls outside this category) are decribed using "features", which
  are advanced and higly customizable descriptors (ie properties, please refer
  to Python documentation if you do not know what a property is).
- the operations that an instrument can perform (such as a measure), are 
  decribed using an "action" that is a simple wrapper around a method. It 
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

.. codeblock::

    class MyDriver(VisaMessageDriver, IEEEIdentify):
        """My driver (suppporting *IDN?) docstring.
        
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
:ref:`dev_driv_standards`

Adding a Feature
----------------

A Feature describes a property lof the instrument, that, as already mentionned 
does not change in a spontaneous way. This restriction comes from the fact that
the values of features are cached. They can and should be discarded when some 
other setting of the driver is modified, but not in a spontaneous manner.

To a add a Feature to your instrument you have nothing else to do that assign
a Feature subclass to an identifier. As illustrated in the example below :

.. codeblock::

    class MyDriver(VisaMessageDriver, IEEEIdentify):
        """My driver (suppporting *IDN?) docstring.
        
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

.. codeblock::

    class MyNewDriver(MyDriver):
        """My driver (suppporting *IDN?) docstring.
        
        """
        mode = set_feat(values=('CW', 'PULSED', 'TRIGGERED'))

The detailed working of Features is detailed in :ref:`dev_driv_features`, and 
all the existing  features are described in the API. Finally, as instruments 
can be often quite surprising in their behaviors, the default behaviors of the
provided features  may prove insufficient. More complex customization are 
possible and detailed in the section :ref:`dev_driv_advanced` of this manual.

Adding an Action
----------------

Actions are light wrapper around methods. They provide similar facility to run
checks and conversion on the input and output values as do features. To declare
one, you only have to declare a method:

.. codeblock::

    class MyDriver(VisaMessageDriver):
        """My driver (suppporting *IDN?) docstring.
        
        """
        
        @Action(values={'kind': ('volt', 'curr')})
        def read_state(self, kind):
            """Read the instrument state.
            
            """
            pass
            
The above ewample shows how to check the value of an argument is valid.

The detailed working of actions is decribed in :ref:`dev_driv_actions` section.
Just like  features several classes of actions exist and are describe in the
API. Actions support advanced customization just like features which are 
described in section :ref:`dev_driv_advanced` 

Using subsystem and channels
----------------------------

Subsystems allow to group features into coherent ensemble, which can allow to 
avoid ridiculously long names. For example many lock-in amplifiers include a
built-in oscillator and subsytems allow for example to group the related 
features such as amplitude and frequency as shown below:

.. codeblock::

    class MyDriver(VisaMessageDriver):
        """My driver (suppporting *IDN?) docstring.
        
        """
        
        oscillator = subsystem()
        with oscillator as o:
        
            o.frequency = Float('OSC:FREQ?', 'OSC:FREQ {}')
            
Actions can also be attached to a subsystems:

.. codeblock::

    class MyDriver(VisaMessageDriver):
        """My driver (suppporting *IDN?) docstring.
        
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
:ref:`dev_driv_subsystem`.

Handling options
----------------

.. todo :: write this section once the implementation is in
