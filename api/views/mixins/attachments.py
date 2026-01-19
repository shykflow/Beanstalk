from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.http import Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
import json

from api.models import (
    Attachment,
    Playlist,
    Experience,
    Post,
)
from api.serializers.attachment import (
    AttachmentViewSerializer,
    AttachmentCreateSerializer,
    AttachmentUpdateSerializer,
)
from api.utils.attachments import (
    AttachmentFileHandler,
)


class AttachmentsMixin:

    @transaction.atomic
    @action(detail=True, methods=['get', 'post'])
    def attachments(self, request: Request, pk) -> Response:
        try:
            instance: Playlist | Experience | Post = self.get_object()
            instance_type = type(instance)
            if instance_type not in (Playlist, Experience, Post):
                raise Exception(f'Need to add support for attachments on {instance_type} type')

            serializer_context = self.get_serializer_context()

            if request.method == 'GET':
                serializer = AttachmentViewSerializer(
                    instance.attachments.order_by('sequence'),
                    many=True,
                    context=serializer_context)
                return Response(serializer.data)

            # POST
            request_data: dict = request.data
            json_data = json.loads(request_data.get('json', '{}'))
            to_create_data: list[dict] = json_data.get('create', [])
            to_update_data: list[dict] = json_data.get('update', [])
            to_delete_ids: list[int] = json_data.get('delete', [])

            serialized_created: list[Attachment] = []
            serialized_updated: list[Attachment] = []
            deleted_ids: list[int] = []

            existing_attachment_count = instance.attachments.count()
            MAX_ATTACHMENTS_ALLOWED = settings.FILE_UPLOADS['ATTACHMENTS']['MAX_ATTACHMENTS_ALLOWED']
            new_number_of_attachments = existing_attachment_count
            new_number_of_attachments += len(to_create_data)
            new_number_of_attachments -= len(to_delete_ids)
            if new_number_of_attachments > MAX_ATTACHMENTS_ALLOWED:
                msg = f'Only {MAX_ATTACHMENTS_ALLOWED} attachments are allowed, ' + \
                    f'this would result in {new_number_of_attachments} attachments'
                raise ValidationError(msg)


            # Validate json values
            for data_dict in to_create_data:
                validator = AttachmentCreateSerializer(
                    data=data_dict,
                    context=serializer_context)
                validator.is_valid(raise_exception=True)
            for data_dict in to_update_data:
                validator = AttachmentUpdateSerializer(
                    data=data_dict,
                    context=serializer_context)
                validator.is_valid(raise_exception=True)

            # Validate all files intended to be attached are properly referenced
            for data_dict in to_create_data:
                file_key = data_dict['file_key']
                file = request.FILES.get(file_key)
                if file is None:
                    raise ValidationError(f'`{file_key}` is not an uploaded file')
                thumbnail_key = data_dict.get('thumbnail_key')
                if thumbnail_key is not None:
                    thumbnail = request.FILES.get(thumbnail_key)
                    if thumbnail is None:
                        raise ValidationError(f'`{thumbnail_key}` is not an uploaded file')

            # Validate the same items to update are not the same to delete
            to_update_ids = [d['id'] for d in to_update_data]
            for id in to_delete_ids:
                if id in to_update_ids:
                    msg = f'Attachment with id={id} cannot be both updated and deleted'
                    raise ValidationError(msg)


            # Create in-memory only attachment and validate its file references
            attachments_to_create: list[Attachment] = []
            for data_dict in to_create_data:
                attachment = Attachment()
                attachment.name = data_dict['name']
                if (attachment.name or '').strip() == '':
                    attachment.name = None
                attachment.description = data_dict['description']
                if (attachment.description or '').strip() == '':
                    attachment.description = None
                attachment.sequence = data_dict['sequence']
                if instance_type is Post:
                    attachment.post = instance
                elif instance_type is Experience:
                    attachment.experience = instance
                elif instance_type is Playlist:
                    attachment.playlist = instance
                file_key = data_dict['file_key']
                file = request.FILES[file_key]
                thumbnail_key = data_dict.get('thumbnail_key')
                thumbnail = None
                if thumbnail_key != None:
                    thumbnail = request.FILES[thumbnail_key]
                file_handler = AttachmentFileHandler(attachment, file, thumbnail)
                file_handler.validate_and_prep_simple_info()
                attachment.type = file_handler._attachment_type
                assert(attachment.type is not None)
                attachment.file_handler = file_handler
                attachments_to_create.append(attachment)

            # Create
            for attachment in attachments_to_create:
                file_handler: AttachmentFileHandler = attachment.file_handler
                attachment.file_handler = None
                file_handler.compress_and_set_files()
                assert(bool(attachment.file))
                attachment.save()
                file_handler.dispose()
                serializer = AttachmentViewSerializer(attachment, context=serializer_context)
                serialized_created.append(serializer.data)

            for data_dict in to_update_data:
                attachment = Attachment.objects \
                    .filter(pk=data_dict['id']) \
                    .first()
                if attachment is None:
                    raise Http404
                for key in data_dict:
                    if key == 'id':
                        continue
                    setattr(attachment, key, data_dict[key])
                attachment.save()
                serializer = AttachmentViewSerializer(attachment, context=serializer_context)
                serialized_updated.append(serializer.data)

            if len(to_delete_ids) > 0:
                to_delete_qs: QuerySet[Attachment] = Attachment.objects \
                    .filter(id__in=to_delete_ids)
                attachment: Attachment
                for attachment in to_delete_qs:
                    attachment.delete()
                    deleted_ids.append(attachment.id)

            validator = AttachmentViewSerializer()
            response_data = {
                'created': serialized_created,
                'updated': serialized_updated,
                'deleted': deleted_ids,
            }
            return Response(response_data, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            transaction.set_rollback(rollback=True)
            if type(e) is ValidationError:
                _e: ValidationError = e
                return Response(_e.message, status=status.HTTP_400_BAD_REQUEST)
            else:
                raise
