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

    Options and checks
    ^^^^^^^^^^^^^^^^^^
    

Channels
--------

    Declaration
    ^^^^^^^^^^^

    Usage
    ^^^^^


