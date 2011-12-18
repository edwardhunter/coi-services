#!/usr/bin/env python

__author__ = 'Ian Katz'
__license__ = 'Apache 2.0'

from pyon.core.exception import BadRequest, NotFound
#from pyon.core.bootstrap import IonObject
from pyon.public import AT
from pyon.util.log import log

######
"""
now TODO

 - implement find methods


Later TODO

 - 

"""
######




class IMSworker(object):
    
    def __init__(self, clients):
        self.clients = clients

        self.iontype  = self._primary_object_name()
        self.ionlabel = self._primary_boject_label()

        self.RR = self.clients.resource_registry
        self.on_worker_init()


    ##################################################
    #
    #    STUFF THAT SHOULD BE OVERRIDDEN
    #
    ##################################################

    def _primary_object_name(self):
        return "YOU MUST SET THIS" #like "InstrumentAgent" or (better) RT.InstrumentAgent

    def _primary_object_label(self):
        return "YOU MUST SET THIS" #like "instrument_agent"

    def on_worker_init():
        return
 
    def on_pre_create(self, obj):
        return 

    def on_post_create(self, obj_id, obj):
        return 

    def on_pre_update(self, obj):
        return
    
    def on_post_update(self, obj):
        return
        
    ##################################################
    #
    #   LIFECYCLE TRANSITION ... THIS IS IMPORTANT
    #
    ##################################################

    def advance_lcs(self, resource_id, newstate):
        """
        attempt to advance the lifecycle state of a resource
        @resource_id the resource id
        @newstate the new lifecycle state
        @todo check that this resource is of the same type as this worker class!
        """
        necessary_method = "lcs_precondition_" + str(newstate)
        if not hasattr(self, necessary_method):
            raise NotImplementedError("Lifecycle precondition method '%s' not defined for %s!" 
                                      % (newstate, self.iontype))

        #FIXME: make sure that the resource type matches self.iontype

        precondition_fn = getattr(self, necessary_method)

        #call the precondition function and react
        if precondition_fn(self, resource_id):
            log.debug("Moving %s resource to state %s" % (self.iontype, newstate))
            self.RR.execute_lifecycle_transition(resource_id=resource_id, lcstate=newstate)
        else:
            raise BadRequest("Couldn't transition %s to state %s; failed precondition" 
                             % (self.iontype, newstate))

    # so, for example if you want to transition to "NEW", you'll need this:
    #
    def lcs_precondition_NEW(self, resource_id): 
        return True






    ##################################################
    #
    #    HELPER METHODS
    #
    ###################################################

    # find whether a resource with the same type and name already exists
    def _check_name(self, resource_type, primary_object, verb):
        if not hasattr(primary_object, "name"):
            raise BadRequest("The name field was not set in the resource %s" % verb)

        name = primary_object.name
        try:
            found_res, _ = self.RR.find_resources(resource_type, None, name, True)
        except NotFound:
            # New after all.  PROCEED.
            pass
        else:
            if 0 < len(found_res):
                raise BadRequest("%s resource named '%s' already exists" % (resource_type, name))
        
    # try to get a resource
    def _get_resource(self, resource_type, resource_id):
        resource = self.RR.read(resource_id)
        if not resource:
            raise NotFound("%s %s does not exist" % (resource_type, resource_id))
        return resource

    # return a valid message from a create
    def _return_create(self, resource_label, resource_id):
        retval = {}
        retval[resource_label] = resource_id
        return retval

    # return a valid message from an update
    def _return_update(self, success_bool):
        retval = {}
        retval["success"] = success_bool
        return retval

    # return a valid message from a read
    def _return_read(self, resource_type, resource_label, resource_id):
        retval = {}
        resource = self._get_resource(resource_type, resource_id)
        retval[resource_label] = resource
        return retval

    # return a valid message from a delete
    def _return_delete(self, success_bool):
        retval = {}
        retval["success"] = success_bool
        return retval

    # return a valid message from an activate
    def _return_activate(self, success_bool):
        retval = {}
        retval["success"] = success_bool
        return retval

    ##########################################################################
    #
    # CRUD methods
    #
    ##########################################################################

    def create_one(self, primary_object={}):
        """
        method docstring
        """
        # make sure ID isn't set
        if hasattr(primary_object, "_id"):
            raise BadRequest("ID field was pre-defined for a create %s operation" % self.iontype)

        # Validate the input filter and augment context as required
        self._check_name(self.iontype, primary_object, "to be created")

        #FIXME: more validation?
        self.on_pre_create(primary_object)

        #persist
        #primary_object_obj = IonObject(self.iontype, primary_object)
        primary_object_id, _ = self.RR.create(primary_object)

        self.on_post_create(primary_object_id, primary_object)

        return self._return_create("%s_id" % self.ionlabel, primary_object_id)


    def update_one(self, primary_object={}):
        """
        method docstring
        """
        if not hasattr(primary_object, "_id"):
            raise BadRequest("The _id field was not set in the %s resource to be updated" % self.iontype)

        #primary_object_id = primary_object._id
        #
        #primary_object_obj = self._get_resource(self.iontype, primary_object_id)        

        # Validate the input 
        self.on_pre_update(primary_object)
        
        #if the name is being changed, make sure it's not being changed to a duplicate
        self._check_name(self.iontype, primary_object, "to be updated")

        #persist
        self.RR.update(primary_object)

        self.on_post_update(primary_object)

        return self._return_update(True)

        

    def read_one(self, primary_object_id=''):
        """
        method docstring
        """
        return self._return_read(self.iontype, self.ionlabel, primary_object_id)



    def delete_one(self, primary_object_id=''):
        """
        method docstring
        """

        primary_object_obj = self._get_resource(self.iontype, primary_object_id)        
        
        self.RR.delete(primary_object_obj)
        
        return self._return_delete(True)

        # Return Value
        # ------------
        # {success: true}
        #
        pass



    def find_some(self, filters={}):
        """
        method docstring
        """
        # Return Value
        # ------------
        # primary_object_list: []
        #
        raise NotImplementedError()
        pass


    #########################################################
    #
    # ASSOCIATION METHODS
    #
    #########################################################

    def _assn_name(self, association_type):
        return {
            AT.hasModel              : lambda: "hasModel",
            AT.hasAssignment         : lambda: "hasAssignment",
            AT.hasPlatform           : lambda: "hasPlatform",
            AT.hasAgentInstance      : lambda: "hasAgentInstance",
            AT.hasAgent              : lambda: "hasAgent",
            AT.hasInstrument         : lambda: "hasInstrument",
            AT.hasSensor             : lambda: "hasSensor",
            AT.hasInstance           : lambda: "hasInstance",
            AT.hasDataProducer       : lambda: "hasDataProducer",
            AT.hasChildDataProducer  : lambda: "hasChildDataProducer",
            }[association_type]()


    def link_resources(self, subject_id='', association_type='', object_id=''):
        associate_success = self.RR.create_association(subject_id, 
                                                       association_type, 
                                                       object_id)

        log.debug("Create %s Association: %s" % (self._assn_name(association_type), 
                                                 str(associate_success)))
        return associate_success

    def unlink_resources(self, subject_id='', association_type='', object_id=''):
        
        assoc = self.RR.get_association(subject=subject_id, predicate=association_type, object=object_id)
        dessociate_success = self.RR.delete_association(assoc)

        log.debug("Delete %s Association: %s" % (self._assn_name(association_type), 
                                                 str(dessociate_success)))
        return dessociate_success

