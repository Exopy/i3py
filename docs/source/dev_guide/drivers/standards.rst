.. _dev_driv_standards

.. include:: ../substitutions.sub

Standards
=========

In order to improve inter-operalibility and allow, up to point, to replace one
instrument with another equivalent one, it is crucial for both instrument 
interfaces to expose the same API to the user. I3py strives to achieve this
kind of interoperability. Of course, it can never be perfect as commonly some
instrument implement very specific behaviors not found in other. Furthermore,
one must accept that generality may mean that the interface may not appear as 
simple as it could be because it takes into account possible variations in 
other instruments. One example is the one of the instrument output (voltage,
microwave power, ...) in many cases one can find equivalent instruments with
multiple outputs which is why the output of an instrument is often represented 
as a channel. This allows to simply change the output id when swapping two 
instruments. By convention, the id used for single output instruments is 0.

Trying to figure out, the "right" interface for a class of instrument is a 
tedious task that requires to consider for the initial design two or three 
instrument from different vendors. However once this work is done, implementing
new drivers becomes straightforward. In addition, one can implement generic 
behaviors as part of a standard: the case of IEEE * commands is one example and
the SCPI 'SYSTem:ERRor?' is another. Implementing those behaviors once in a 
standard allow to trivially support them in all instruments and limit code 
duplication.

To allow to use standards at any level of a hierarchy (top driver, subsytem, 
channel), all standards are implemented as simply inheriting |HasFeatures|.
To use them they simply need to be added to the base classes of the component 
in which they belong.
