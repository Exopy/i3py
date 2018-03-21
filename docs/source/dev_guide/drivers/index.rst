.. _dev-drivers:

Driver machinery
================

I3py strives to provide a convenient but flexible interface to write drivers
that can handle the full complexity of the instrument you need to interface.
Of course this has some cost in term of internal complexity, but those are
believed to be worth it.

This section of the documentation will first take you through the notions used
in I3py to structure your driver, and how to use them to write your driver. It
will try to remain generic but will use the case of instruments controlled
through the VISA protocol to illustrate the examples as it is a very common
case.

Once this done, the following sections will dive in the detailed working of
the different components making up a driver, and will explore in more details
some of the notions previously presented. The reading of those sections is not
mandatory to write a driver but will help you understand the inner working
of I3py and help you tackle more challenging driver designs.

.. toctree::
    :numbered:
    :maxdepth: 2

    overview
    features
    actions
    channels_subsystems
    advanced_customizing
    standards
