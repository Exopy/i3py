.. include:: ../../substitutions.sub

.. _dev-driv-features:

Features
========

Features are descriptors just like standard Python property. They live on the
class and define what happens when one gets or set the attribute associated
with the feature on a class instance, that is to say when one writes:

.. code-block:: python

    a = d.myfeature

or:

.. code-block:: python

    d.myfeature = 1

The following sections will describe the different steps involved in the
getting and setting process and how they can be customized using the different
arguments it takes. Even more advanced customizations are possible and will be
described in their own part :ref:`dev-driv-advanced`.

Working principle
-----------------

First we will describe the process involved in retrieving a feature value
then switch to describing the setting of it.

.. note::

    The first two arguments of a feature are always the getter and setter.
    If their value is set to None, the corresponding operation won't be
    possible for the feature. A feature is always deletable and deleting it
    corresponds to discarding the cached value if any exists.

Getting chain
^^^^^^^^^^^^^

First when getting a feature, we check if the instrument options allow
to access it, and if not an AttributeError is raised. Next, we check
whether or not its current value is known. If it is, the cached value
is directly returned otherwise the system proceed with the retrieval
sequence, in three steps as follows:

- |Feature.pre_get|:
  This step is in charge to check that we can actually retrieve the
  value from the instrument. Some assertions about the instrument
  current state can for example be performed.

- |Feature.get|:
  This step is tasked with the actual communication with the
  instrument. It should retrieve the value from the instrument and
  pass to the next step without performing any conversion. By default,
  it will call the |HasFeatures.default_get_feature| method defined on
  the class it belongs and pass it the value of the getter argument
  passed to the feature when it was created.

- |Feature.post_get|:
  This step is tasked with converting the value obtained at the get
  step into a more user friendly representation than what was returned
  by the instrument. It can for example extract the meaningful part
  of the instrument response and turn it into the proper type, such as
  an integer or a float. It can also check for an error state on the
  instrument even so get operation should not cause any issue and such
  checks be left to setting.

The value coming out of the post_get step is cached and then returned
to the user. If an error occurs during any of the step, if it is one
of the ones listed in the retries_exceptions attribute of the driver
the connection will be closed and re-opened and the operation attempted
anew. Otherwise or if the re-opening fails too many times (more than
specified in the retries argument of the feature), an |I3pyFailedGet|
exceptions will be raised while still pointing to the original errors.


Setting chain
^^^^^^^^^^^^^

First when setting a feature, we check if the instrument options allow
to access it, and if not an AttributeError is raised. Next, the value
is checked against the cached value. If both values are found to be
equal, the set is not performed as it would be useless. Otherwise, we
proceed with the setting sequence, which, like the getting, happens in
three steps:

- |Feature.pre_set|:
  During this step, the state of the instrument can be checked and the
  value passed by the user validated and converted to a format
  appropriate to pass to the instrument.

- |Feature.set|:
  This step is dedicated to actually communicating with the instrument
  to set the value. If the instrument returns any value that can be
  used to check that the operation went without issue, it should be
  returned so that it can be passed up to the next method. By default,
  it will call the |HasFeatures.default_set_feature| method defined on
  the class it belongs and pass it the value of the setter argument
  passed to the feature when it was created.

- |Feature.post_set|:
  This step main goal is to check that the operation of setting the
  value went without trouble. By default, it simply calls the
  |HasFeatures.default_check_operation| on the parent class.

Once the value has been set and if no error occured, the value
specified by the user is cached.  If an error occurs during any of the
step, if it is one of the ones listed in the retries_exceptions
attribute of the driver the connection will be closed and re-opened
and the operation attempted anew. Otherwise or if the re-opening fails
too many times (more than specified in the retries argument of the
feature), an |I3pyFailedSet| exceptions will be raised while still
pointing to the original errors.

Usual configurations
--------------------

In addition to the 'getter' and 'setter' previously mentioned I3py features
provides a number of often required checks, data extraction and data conversion
utilities. The following list illustrates them:

- 'options': available on all |Feature| subclasses
  A ; separated list of checks to perform on options values to determine if
  the Feature can be used. Options are defined using the |Options| feature.
  The test is performed a single time and then cached.

- 'checks': available on all |Feature| subclasses
  Similar to options, but can be used to check any value and is performed
  each time the feature is get or set.

- 'extract': available on all |Feature| subclasses
  A format string specifying how to extract the value of interest from the
  instrument response.

- 'discard': available on all |Feature| subclasses
  A list of features whose cache value should be discarded when the feature
  value is set. Alternatively a dict whose keys are 'features' and 'limits'
  can be used to also specify to discard some cached limits.

- 'values': available on |Str|, |Int| and |Float|
  A tuple of acceptable values for the feature.

- 'mapping': available on |Str|, |Int| and |Float|
  A mapping between user meaningful values and instrument meaningful ones.

- 'limits': available on |Int| and |Float|
  A 2-tuple, 3-tuple or str specifying the minimal and maximal values
  allowed and optionally the resolution that the feature can take. In the
  case of a str, the string specifies the named limit to use (see the
  following paragraph about defining limits).

- 'aliases': available on |Bool|
  A dictionary whose keys are True and False and whose values (list)
  specifies accepted aliases for True and False for setting.

.. note::

    In many cases, the range of allowed values for a specific feature is not
    fixed but may be related to another feature value. To handle this case,
    I3py allows to define dynamic limits using the |limits| decorator. The
    decorated method should return an instance of |IntLimitsValidator| or
    |FloatLimitsValidator| depending the kind of value this limit applies to.


Specialized features
^^^^^^^^^^^^^^^^^^^^

- The |Alias| feature is a special feature allowing to delegate the actual
  work of getting/setting to another feature.

- The |Register| is a specialized feature which can be used to get and set
  the value of a binary register such as the ones commonly used by VISA based
  instrument. It will create a dedicated subclass of IntFlag and will handle
  the conversion. It takes two special arguments:

    + names: a list of names describing each bit in order (from least
      significant to most significant) or a dictionary mapping each name to the
      bit it describe. Those names should be valid python attribute names and
      ideally be all upper case.

    + length: the length of the register (8 by default but some instrument use
      16 bits register).


Flexible getter/setter
----------------------

In some cases, the command to use to get/set a Feature may depend on the state
of the instrument. This use case can be handled by using a custom get/set
method as described in :ref:`dev-driv-advanced`. However as such cases can be
quite common, I3py provides an alternative mechanism based on factory class to
which the building of the get/set method can be deferred. Such factory classes
should inherit from |AbstractGetSetFactory| and can be used for the
getter/setter arguments of a feature.

The factories implemented in I3py can be found in
`i3py.core.features.factories`.
