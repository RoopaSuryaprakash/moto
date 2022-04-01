from ._base_response import EC2BaseResponse


class AmisResponse(EC2BaseResponse):
    def create_image(self):
        name = self.querystring.get("Name")[0]
        description = self._get_param("Description", if_none="")
        instance_id = self._get_param("InstanceId")
        tag_specifications = self._get_multi_param("TagSpecification")
        if self.is_not_dryrun("CreateImage"):
            image = self.ec2_backend.create_image(
                instance_id,
                name,
                description,
                tag_specifications=tag_specifications,
            )
            template = self.response_template(CREATE_IMAGE_RESPONSE)
            return template.render(image=image)

    def copy_image(self):
        source_image_id = self._get_param("SourceImageId")
        source_region = self._get_param("SourceRegion")
        name = self._get_param("Name")
        description = self._get_param("Description")
        if self.is_not_dryrun("CopyImage"):
            image = self.ec2_backend.copy_image(
                source_image_id, source_region, name, description
            )
            template = self.response_template(COPY_IMAGE_RESPONSE)
            return template.render(image=image)

    def deregister_image(self):
        ami_id = self._get_param("ImageId")
        if self.is_not_dryrun("DeregisterImage"):
            success = self.ec2_backend.deregister_image(ami_id)
            template = self.response_template(DEREGISTER_IMAGE_RESPONSE)
            return template.render(success=str(success).lower())

    def describe_images(self):
        self.error_on_dryrun()
        ami_ids = self._get_multi_param("ImageId")
        filters = self._filters_from_querystring()
        owners = self._get_multi_param("Owner")
        exec_users = self._get_multi_param("ExecutableBy")
        images = self.ec2_backend.describe_images(
            ami_ids=ami_ids, filters=filters, exec_users=exec_users, owners=owners
        )
        template = self.response_template(DESCRIBE_IMAGES_RESPONSE)
        return template.render(images=images)

    def describe_image_attribute(self):
        ami_id = self._get_param("ImageId")
        groups = self.ec2_backend.get_launch_permission_groups(ami_id)
        users = self.ec2_backend.get_launch_permission_users(ami_id)
        template = self.response_template(DESCRIBE_IMAGE_ATTRIBUTES_RESPONSE)
        return template.render(ami_id=ami_id, groups=groups, users=users)

    def modify_image_attribute(self):
        ami_id = self._get_param("ImageId")
        operation_type = self._get_param("OperationType")
        group = self._get_param("UserGroup.1")
        user_ids = self._get_multi_param("UserId")
        if self.is_not_dryrun("ModifyImageAttribute"):
            if operation_type == "add":
                self.ec2_backend.add_launch_permission(
                    ami_id, user_ids=user_ids, group=group
                )
            elif operation_type == "remove":
                self.ec2_backend.remove_launch_permission(
                    ami_id, user_ids=user_ids, group=group
                )
            template = self.response_template(MODIFY_IMAGE_ATTRIBUTE_RESPONSE)
            return template.render()

    def register_image(self):
        name = self.querystring.get("Name")[0]
        description = self._get_param("Description", if_none="")
        if self.is_not_dryrun("RegisterImage"):
            image = self.ec2_backend.register_image(name, description)
            template = self.response_template(REGISTER_IMAGE_RESPONSE)
            return template.render(image=image)

    def reset_image_attribute(self):
        if self.is_not_dryrun("ResetImageAttribute"):
            raise NotImplementedError(
                "AMIs.reset_image_attribute is not yet implemented"
            )


CREATE_IMAGE_RESPONSE = """<CreateImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  
</CreateImageResponse>"""

COPY_IMAGE_RESPONSE = """<CopyImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   
</CopyImageResponse>"""

# TODO almost all of these params should actually be templated based on
# the ec2 image
DESCRIBE_IMAGES_RESPONSE = """<DescribeImagesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  
</DescribeImagesResponse>"""

DESCRIBE_IMAGE_RESPONSE = """<DescribeImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  
</DescribeImageAttributeResponse>"""

DEREGISTER_IMAGE_RESPONSE = """<DeregisterImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  
</DeregisterImageResponse>"""

DESCRIBE_IMAGE_ATTRIBUTES_RESPONSE = """
<DescribeImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  
</DescribeImageAttributeResponse>"""

MODIFY_IMAGE_ATTRIBUTE_RESPONSE = """
<ModifyImageAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
 
</ModifyImageAttributeResponse>
"""

REGISTER_IMAGE_RESPONSE = """<RegisterImageResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
 
</RegisterImageResponse>"""
