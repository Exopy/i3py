.. include:: ../../substitutions.sub

.. _dev-driv-actions:

Actions
=======

Actions are the equivalent of features for methods. While features allows
custom access to attributes, actions allow custom access and calling of
methods. They allow in particular to specify checks or conversions on the
methods arguments and return values.

The following sections will describe the different steps involved when calling
an Action and how they can be customized using the different arguments it
takes. Even more advanced customizations are possible and will be described in
their own part :ref:`dev-driv-advanced`.

.. note::

    If some cases, an action may start an operation that the instrument will
    take a long time to process. In such a case it is best to return an
    |InstrJob| object that can be used at the appropriate time to wait for
    completion than to block for a long time.

Working principle
-----------------

When accessing an Action (d.action), we check first if the instrument options
allow to access it, and if not an AttributeError is raised. Under normal
circumstances, Python would return a bound method than we can next call. For
actions, we return an |ActionCall| which takes in charge to run the three steps
of the call:

    - |BaseAction.pre_call|:
      This step is in charge to check that we can actually perform the
      wrapped action. Some assertions about the instrument current state
      and argument values can for example be performed.

    - |BaseAction.call|:
      Call the wrapped method passing as argument the argument as returned
      by the pre-call step.

    - |BaseAction.post_call|:
      This step is tasked with converting the return values of the call and
      running some additional checks.

Usual configurations
--------------------

In addition to the 'getter' and 'setter' previously mentioned I3py features
provides a number of often required checks, data extraction and data conversion
utilities. The following list illustrates them:

	- 'options': available on all |BaseAction| subclasses

      A ; separated list of checks to perform on options values to determine if
      the Action can be used. Options are defined using the |Options| feature.
      The test is performed a single time and then cached.

	- 'checks': available on |Action|

      A ; separated list of checks to perform each time the action is called.
      All the method arguments are available in the assertion execution
      namespace so one can access to the driver using self and to the arguments
      using their name (the signature of the wrapper is made to match the
      signature of the wrapped method).

	- 'values': available on |Action|

      A dictionary mapping the argument names to their allowed values (tuple).
      Arguments not listed in this dictionary are simply not validated.

	- 'limits': available on |Action|

      A dictionary mapping the argument names to their limits. Arguments not
      listed in this dictionary are simply not validated. Limits can be a
      2-tuple, 3-tuple or str specifying the minimal and maximal values
      allowed and optionally the resolution that the feature can take. In the
      case of a str, the string specifies the named limit to use (see
      :ref:`dev-driv-features` about defining limits).

.. note::

    The |RegisterAction| is a specialized action which can be used to read the
    value of a binary register such as the ones commonly used by VISA based
    instrument. It will create a dedicated subclass of IntFlag and will handle
    the conversion. It takes two arguments:

    - names: a list of names describing each bit in order (from least
      significant to most significant) or a dictionary mapping each name to the
      bit it describe.

    - length: the length of the register (8 by default but some instrument use
      16 bits register).
