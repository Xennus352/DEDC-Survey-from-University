"""Readable values for reports and exports; stored answers are never rewritten."""


def label(value):
    return str(value).replace('_', ' ').replace('.', ' ').capitalize()


def audit_action(action):
    special = {
        'auth.login': 'Signed in', 'auth.logout': 'Signed out',
        'workbook.excel_export': 'Workbook exported to Excel',
    }
    if action in special:
        return special[action]
    noun, _, verb = action.rpartition('.')
    verbs = {'create': 'created', 'edit': 'updated', 'update': 'updated',
             'delete': 'deleted', 'publish': 'published', 'duplicate': 'duplicated',
             'archive': 'archived', 'restore': 'restored', 'review': 'reviewed',
             'import': 'imported', 'export': 'exported', 'upload': 'uploaded'}
    return f'{label(noun)} {verbs[verb]}' if noun and verb in verbs else label(action)


def value_text(value):
    if value is None:
        return 'No answer'
    if value is True:
        return 'Yes'
    if value is False:
        return 'No'
    if value == '':
        return 'Empty text'
    if isinstance(value, list):
        return '; '.join(value_text(item) for item in value) if value else 'No selections'
    if isinstance(value, dict):
        return '\n'.join(f'{label(key)}: {value_text(item)}' for key, item in value.items()) if value else 'No values'
    return str(value)


def answer_text(question, value, filename=None):
    if value is None:
        return 'No answer'
    if question.kind in {'file', 'image'} and isinstance(value, dict):
        return filename or f"Attachment #{value.get('file_id', 'unknown')}"
    if question.kind == 'repeating_group' and isinstance(value, list):
        fields = {field['key']: field.get('title', field['key']) for field in question.config.get('fields', [])}
        return '\n'.join(
            f"Row {index}: " + '; '.join(f'{fields.get(key, label(key))}: {value_text(item)}' for key, item in row.items())
            for index, row in enumerate(value, 1)
        ) if value else 'No rows'
    if question.kind in {'single_choice', 'multiple_choice', 'dropdown', 'radio', 'checkboxes'}:
        choices = {option.value: option.label for option in question.options}
        if isinstance(value, list):
            return '; '.join(choices.get(item, str(item)) for item in value) if value else 'No selections'
        return choices.get(value, value_text(value))
    return value_text(value)
