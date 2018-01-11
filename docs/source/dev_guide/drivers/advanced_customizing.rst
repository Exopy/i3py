.. _dev_driv_advanced

.. include:: ../substitutions.sub

Advanced customization
======================

The mechanisms presented in the previous sections allow to handle a large
number of situation occurring in real life instrument. However, in instruments,
there are corner cases, and those are actually not so rare and require to be
handled as gracefully as possible.

To handle those cases, I3py allows to customize the pre_get/set/call,
get/set/call, post_get/set/call of features and actions either by replacing
them by hand written function or by stacking on the existing behaviors custom
functions. The following sections will present the mechanisms involved.

Defining custom handler
-----------------------

Custom handlers can be defined using the following syntax:

.. codeblock::

    from i3py.core import customize

    class MyDriver(VisaMessageDriver, IEEEIdentify):
        """My driver (supporting *IDN?) docstring.

        """
        mode = Unicode('MODE?', 'MODE {}', values=('CW', 'PULSED'))

        @customize('mode', 'post_get')
        def _custom_mode_post_get(feat, driver, value)->Any:
            print(f'Read mode {value}')
            return value

Let examine in details how this works. First we import the |customize|
decorator. |customize| is actually a class, which we first instantiate. We pass
it the name of the feature/action on which it should apply, and the name of the
method of this descriptor that should be customized. Because, we did not
specify any additional argument the customization function will replace the
existing one. This is the simplest way to use the customization mechanism, but
it does not allow to combine existing mechanism with custom behavior. How to
achieve this will be discussed in the next section.

Next, we use to decorate a function. **BE CAREFUL HERE**, even though we are in
the body of a class, this function won't be bound as a method of this class,
which is why we **DO NOT USE** self as first argument because it
**WILL NOT BE** the first argument this function will take. With that in mind,
one can notice that the signature of the function matches the signature of the
descriptor method to customize. Actually, it should match the signature exactly
(using the same argument names). Only self can be aliased to 'feat' when
customizing a feature and 'action' for actions, for the sake of clarity.

.. note::

    As the exact signature of the action, may be painful to emulate one can use
    instead `(action, driver, *args, **kwargs)`.

As this mechanism is quite advanced, it is picky and one must be careful when
using it. First, as already mentioned, the signature must be an exact match
for input arguments but additionally one must be careful to return the expected
value:

- None for |Feature.pre_get| and |Feature.post_set|
- a value for |Feature.get| and |BaseAction.call|
- the processed value for |Feature.post_get|, |Feature.pre_set| and
  |BaseAction.post_call|
- a potential answer from the instrument for |Feature.set|
- a tuple of argument and a dictionary of keyword arguments for
  |BaseAction.pre_call|


Composing custom behavior and existing ones
-------------------------------------------

When one needs an existing behavior (such as 'checks') and a custom on the same
method, replacing the existing method would not be effective. To circumvent,
this issue I3py allow to pass an additional behavior to customize to indicate
that it should chain the call of the custom method and the existing one.
To chain the calls, it will effectively replace the customized function by
a |MethodComposer| instance which when called will call the chained functions.

The third argument of customize allow to specify how to perform the
composition. It must be a tuple even when it contains a single argument and the
possible values are the following:

- ('prepend',)
- ('add_before', existing_id)
- ('add_after', existing_id)
- ('append',)
- ('replace', existing_id)
- ('remove', exising_id)

The existing_id is a string allowing to identify the function with respect to
which 'position' the customization. For built-in functionalities, it matches
the keywords argument that was used to create it ('checks' for example).

.. note::

    When a feature use multiple builtin mechanisms, those are composed using
    the same principle.

.. note::

    Customization are also given an id. By default, it is simply custom, but
    one can specify a different value as the fourth argument to |customize|.

The way to chain the calls depends on the builtin function already present and
the goal of the customization. For example, a custom conversion in a get may
need to occur after the value was extracted from the instrument answer.
