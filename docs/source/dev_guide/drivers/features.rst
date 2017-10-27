.. _dev_driv_features

.. include:: ../substitutions.sub

Features
========

Features are descriptors just like standard Python property. They live on the 
class and define what happens when one gets or set the attribute associated 
with the feature on a class instance, that is to say when one writes:

.. codeblock:
    
    a = d.myfeature

or:

.. codeblock:

    d.myfeature = 1

The following sections will describe the different steps involved in the 
getting and setting process and how they can be customized using the different 
arguments it takes. Even more advanced customizations are possible and will be
described in their own part :ref:`dev_driv_advanced`. 
    
Working principle
-----------------

    First we will describe the process involved in retrieving a feature value
    then switch to describing the setting of it.
	
	.. note::
	
		The first two arguments of a feature are always the getter and setter.
		If their value is set to None, the feature the corresponding operation
		won't be possible for the feature. A feature is always deletable and 
		deleting it conrresponds to discarding the cached value if any exists.

    Getting chain
    ^^^^^^^^^^^^^
    
        First when getting a feature, we check if the instrument options allow
		to access it, and if not an AttributeError is raised. Next, we check
		whether or not its current value is known. If it is, the cached value 
		is directly returned otherwise the system proceed with the retrieval 
		sequence, in three steps as follows:
        
        - |Feature.pre_get|: 
          This setp is in charge to check that we can actually retrieve the
          value from the instrument. Some assertions about the instrument 
          options and current state can for example be performed.
          
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

In addition to the 'getter' and 'setter' previously mentionned I3py features 
provides a number of often required checks, data extraction and data conversion
utilities. The following list illustrates them:

	- 'options': available on all Feature subclasses

	- 'checks': available on all Feature subclasses
	  
	- 'extract': available on all Feature subclasses
	
	- 'discard': available on all Feature subclasses
	
	- 'values': available on Str, Int and Float
	
	- 'mapping': available on Str, Int and Float
	
	- 'limits': available on Int and Float
	
	- 'aliases': available on Bool
	

.. note::
	
	.. todo:: add description of limits definition
	
.. note::

	.. todo:: add special description for Alias
	
.. note::

	.. todo:: add special description for Register


Flexible getter/setter
----------------------

.. todo:: describe the use of factories

