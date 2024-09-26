import logging
import traceback
# from .app_1 import callback, message_queue, get_summary
import uuid
import os
from .query_process import query, message_queue
from asgiref.sync import async_to_sync
from .models import FileStructure
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import ValidationError
import json
import asyncio
from threading import Thread
import time



logger = logging.getLogger(__name__)
User = get_user_model()

logger = logging.getLogger(__name__)

class AsyncChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'chat'
        self.session_id = str(uuid.uuid4())

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"WebSocket connection established: {self.channel_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket disconnected: {self.channel_name}, code: {close_code}")

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        content = text_data_json['message']
        input_data = {
            "messages": [{"role": "user", "content": content}],
            "context": text_data_json['code'],
            "session_id": self.session_id,
            "user_id": text_data_json['userId'],
            'thread_id': text_data_json.get('threadId', 'default123'),
            "image_data": text_data_json['image']
        }

        asyncio.create_task(self.process_query(input_data))

    async def process_query(self, input_data):
        try:
            await query(input_data, self.channel_name)
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            await self.chat_message({
                'text': f"An error occurred while processing your request: {str(e)}",
                'sender': "System",
                'thread_id': input_data['thread_id'],
            })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': {
                'text': event['text'],
                'sender': event['sender'],
                'threadId': event.get('thread_id', 'default'),
            }
        }))


class FileStructureConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("Attempting to connect...")
        try:
            query_string = self.scope['query_string'].decode()
            params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
            user_id = params.get('user_id')

            if user_id:
                self.user = await database_sync_to_async(User.objects.get)(id=user_id)
            else:
                # Handle the case when no user_id is provided
                # This could be creating a temporary user or using some default user
                # The exact implementation depends on your application's requirements
                self.user = await database_sync_to_async(User.objects.get)(id=1)  # Example: get a default user

            await self.accept()
            logger.info(f"WebSocket connected for user: {self.user}")

            # Send initial structure immediately after connection
            await self.send_structure()

        except User.DoesNotExist:
            logger.error(f"User with id {user_id} does not exist")
            await self.close()
        except Exception as e:
            logger.error(f"Error in connect method: {str(e)}")
            logger.error(traceback.format_exc())
            await self.close()

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected for user: {getattr(self, 'user', 'Unknown')} with code: {close_code}")

    async def receive(self, text_data):
        # logger.info(f"Received message: {text_data}")
        try:
            data = json.loads(text_data)
            action = data['action']
            if action == 'get_structure':
                await self.send_structure()
            elif data['action'] == 'update_file_content':
                await self.update_file_content(data['id'], data['content'])
            elif action == 'get_file_content':
                await self.get_file_content(data['id'], data.get('name'))
            elif action == 'update_file_content':
                await self.update_file_content(data['id'], data['content'])
            elif action == 'update_node' or action == 'rename_node':
                new_name = data['newName']
                if isinstance(new_name, dict):
                    new_name = new_name.get('name', '')
                await self.rename_node(data['id'], new_name)
            elif action == 'delete_node':
                await self.delete_node(data['id'])
            elif action == 'add_node':
                await self.add_node(data['parentId'], data['node'])
            elif action == 'get_file_path':
                await self.get_file_path(data['id'])
            else:
                logger.warning(f"Received unknown action: {action}")
        except KeyError as e:
            logger.error(f"Missing key in received data: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Missing key in request: {str(e)}'
            }))
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")
        except Exception as e:
            logger.error(f"Error in receive method: {str(e)}")
            logger.error(traceback.format_exc())

    @database_sync_to_async
    def _get_file_content(self, file_id):
        try:
            file = FileStructure.objects.get(id=file_id, user=self.user, type='file')


            if file.name == 'main.py' and file.parent and file.parent.name == 'Project' and file.parent.parent and file.parent.parent.name == 'Root':
                file.content = '''# Welcome to your first Python project!

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
                file.save()
                logger.info(f"Set default content for main.py in Project folder")
            else:
                file.content = ''
                file.save()
                logger.info(f"Set empty content for new file: {file.name}")

            logger.info(f"Returning content for file {file_id} ({file.name}): {file.content[:50]}...")
            return file.content
        except FileStructure.DoesNotExist:
            logger.error(f"File with id {file_id} does not exist for user {self.user}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in _get_file_content: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def get_file_content_for_container(user, file_path, base_path):
        try:
            logger.info(
                f"Attempting to retrieve file content for path: {file_path} for user: {user}, base path: {base_path}")

            # Remove leading './' if present
            file_path = file_path.lstrip('./')

            # Combine base_path and file_path
            full_path = os.path.normpath(os.path.join(base_path, file_path))
            logger.info(f"Full path: {full_path}")

            # Split the path into parts
            path_parts = full_path.split('/')

            # Traverse the file structure
            current_folder = None
            for part in path_parts[:-1]:
                if current_folder is None:
                    current_folder = FileStructure.objects.get(user=user, name=part, parent=None)
                else:
                    current_folder = FileStructure.objects.get(user=user, name=part, parent=current_folder)
                logger.info(f"Traversed to folder: {part}")

            # Get the file from the last folder
            file_name = path_parts[-1]
            if current_folder:
                file = FileStructure.objects.get(user=user, name=file_name, parent=current_folder, type='file')
            else:
                file = FileStructure.objects.get(user=user, name=file_name, parent=None, type='file')

            logger.info(f"Found file: {file.name}")

            if not file.content:
                file.content = ''
                file.save()
                logger.info(f"Set empty content for file: {file.name}")

            logger.info(f"Returning content for file {full_path}: {file.content[:50]}...")
            return file.content
        except FileStructure.DoesNotExist:
            logger.error(f"File with path {full_path} does not exist for user {user}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_file_content: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    async def get_file_content(self, file_id, file_name=None):
        try:

            # Ensure file_id is an integer
            file_id = int(file_id)

            file = await database_sync_to_async(FileStructure.objects.get)(id=file_id, user=self.user)
            file_content = file.content if file.content is not None else ''
            file_name = file_name or file.name

            await self.send(text_data=json.dumps({
                'type': 'file_content',
                'id': file_id,
                'name': file_name,
                'content': file_content
            }))
            logger.info(f"Sent content for file {file_id}")
        except ValueError:
            logger.error(f"Invalid file ID: {file_id}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid file ID'
            }))
        except FileStructure.DoesNotExist:
            logger.error(f"File with id {file_id} does not exist for user {self.user}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'File not found'
            }))
        except Exception as e:
            logger.error(f"Error getting file content: {str(e)}")
            logger.error(traceback.format_exc())
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to get file content'
            }))

    async def update_file_content(self, file_id, content):
        try:
            # Log the incoming data
            logger.info(f"Updating file content for file ID: {file_id}, User: {self.user}")

            # Ensure file_id is an integer
            file_id = int(file_id)

            file = await database_sync_to_async(FileStructure.objects.get)(id=file_id, user=self.user)
            file.content = content if content is not None else ''
            await database_sync_to_async(file.save)()
            logger.info(f"File content updated successfully for file ID: {file_id}")

            await self.send(text_data=json.dumps({
                'type': 'file_content_updated',
                'id': file_id,
                'message': 'File content updated successfully'
            }))
        except ValueError as e:
            logger.error(f"Invalid file ID: {file_id}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid file ID'
            }))
        except FileStructure.DoesNotExist:
            logger.error(f"File not found: {file_id}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'File not found'
            }))
        except Exception as e:
            logger.error(f"Error updating file content: {str(e)}")
            logger.error(traceback.format_exc())
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to update file content'
            }))

    @database_sync_to_async
    def _update_file_content(self, file_id, content):
        try:
            file = FileStructure.objects.get(id=file_id, user=self.user)
            file.content = content
            file.save()
            logger.info(f"File content updated successfully for file ID: {file_id}")
            return True
        except FileStructure.DoesNotExist:
            logger.error(f"File not found: {file_id}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in _update_file_content: {str(e)}")
            return False


    async def send_structure(self):
        try:
            structure = await self.get_file_structure()
            await self.send(text_data=json.dumps({
                'type': 'file_structure',
                'structure': structure
            }))
            logger.info("File structure sent successfully")
        except Exception as e:
            logger.error(f"Error in send_structure method: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to retrieve file structure'
            }))

    @database_sync_to_async
    def get_file_structure(self):
        if self.user == 'GuestUser':
            structure = self.get_default_structure()
            logger.info(f"Returning default structure for GuestUser: {structure}")
            return structure

        root = FileStructure.objects.filter(user=self.user, parent=None).first()
        if not root:
            root = self.create_default_structure(self.user)
            logger.info(f"Created default structure for new user: {self._serialize_structure(root)}")
        else:
            logger.info(f"Retrieved existing structure for user: {self._serialize_structure(root)}")

        return self._serialize_structure(root)


    def get_default_structure(self):
        # Return a default structure for guest users
        return {
            'id': 'root',
            'name': 'Root',
            'type': 'folder',
            'children': [
                {
                    'id': 'project',
                    'name': 'Project',
                    'type': 'folder',
                    'children': [
                        {
                            'id': 'main_py',
                            'name': 'main.py',
                            'type': 'file',
                            'children': []
                        }
                    ]
                }
            ]
        }

    def create_default_structure(self, user):
        root = FileStructure.objects.create(user=user, name='Root', type='folder')
        project_folder = FileStructure.objects.create(user=user, name='Project', type='folder', parent=root)
        main_py = FileStructure.objects.create(
            user=user,
            name='main.py',
            type='file',
            parent=project_folder,
            content="print('Hello, World!')"
        )
        logger.info(f"Created default 'main.py' with content: {main_py.content}")
        return root

    def _serialize_structure(self, node):
        if not node:
            return None
        serialized = {
            'id': str(node.id),
            'name': node.name,
            'type': node.type,
            'children': []
        }
        if node.type == 'folder':
            children = FileStructure.objects.filter(parent=node)
            serialized['children'] = [self._serialize_structure(child) for child in children]
        return serialized

    @database_sync_to_async
    def _get_node(self, node_id):
        try:
            return FileStructure.objects.get(id=node_id, user=self.user)
        except FileStructure.DoesNotExist:
            logger.error(f"Node with id {node_id} does not exist for user {self.user}")
            raise

    @database_sync_to_async
    def _update_node(self, node, new_name):
        try:
            node.name = new_name
            node.full_clean()  # Validate the model
            node.save()
            return node
        except ValidationError as e:
            logger.error(f"Validation error while updating node: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while updating node: {e}")
            raise

    @database_sync_to_async
    def _get_parent_id(self, node):
        if node.parent:
            return str(node.parent.id)
        return None

    async def rename_node(self, node_id, new_name):
        try:
            logger.info(f"Attempting to rename node {node_id} to {new_name}")
            node = await self._get_node(node_id)
            updated_node = await self._update_node(node, new_name)
            parent_id = await self._get_parent_id(updated_node)

            response = {
                'type': 'node_renamed',
                'node': {
                    'id': str(updated_node.id),
                    'name': updated_node.name,
                    'type': updated_node.type,
                    'parent': parent_id,
                }
            }
            await self.send(text_data=json.dumps(response))
            logger.info(f"Node renamed successfully: {updated_node.name}")
        except FileStructure.DoesNotExist:
            error_msg = f"Node with id {node_id} does not exist"
            logger.error(error_msg)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Node not found'
            }))
        except ValidationError as e:
            error_msg = f"Validation error while renaming node: {str(e)}"
            logger.error(error_msg)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid node name'
            }))
        except Exception as e:
            error_msg = f"Unexpected error renaming node: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to rename node'
            }))

    @database_sync_to_async
    def _delete_node(self, node_id):
        node = FileStructure.objects.get(id=node_id, user=self.user)
        node.delete()

    async def delete_node(self, node_id):
        try:
            await self._delete_node(node_id)
            await self.send(text_data=json.dumps({
                'type': 'node_deleted',
                'id': node_id
            }))
        except Exception as e:
            logger.error(f"Error deleting node: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to delete node'
            }))

    def _serialize_node(self, node):
        return {
            'id': str(node.id),
            'name': node.name,
            'type': node.type,
            'parent': str(node.parent.id) if node.parent else None,
            'children': []  # We don't need to include children for rename operations
        }


    @database_sync_to_async
    def _add_node(self, parent_id, new_node):
        parent = FileStructure.objects.get(id=parent_id, user=self.user)
        new_file = FileStructure.objects.create(
            user=self.user,
            parent=parent,
            name=new_node['name'],
            type=new_node['type'],
            content=''  # Initialize with empty content for files
        )
        return {
            'id': str(new_file.id),
            'name': new_file.name,
            'type': new_file.type,
            'parent': str(parent_id),
            'children': []
        }

    async def add_node(self, parent_id, new_node):
        try:
            added_node = await self._add_node(parent_id, new_node)
            await self.send(text_data=json.dumps({
                'type': 'node_added',
                'node': added_node
            }))
            logger.info(f"Node added: {added_node}")
        except Exception as e:
            logger.error(f"Error adding node: {str(e)}")
            logger.error(traceback.format_exc())  # Log the full traceback
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to add node'
            }))

    async def get_file_path(self, file_id):
        try:
            path = await self._get_file_path(file_id)
            await self.send(text_data=json.dumps({
                'type': 'file_path',
                'id': file_id,
                'path': path
            }))
        except Exception as e:
            logger.error(f"Error getting file path: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to get file path'
            }))

    @database_sync_to_async
    def _get_file_path(self, file_id):
        file = FileStructure.objects.get(id=file_id, user=self.user)
        path = file.name
        current = file
        while current.parent:
            current = current.parent
            path = f"{current.name}/{path}"
        return path