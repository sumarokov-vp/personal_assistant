from src.conversations.models.attachment_availability import AttachmentAvailability
from src.conversations.models.conversation_attachment import ConversationAttachment
from src.conversations.models.conversation_message import ConversationMessage
from src.conversations.models.message_summary import MessageSummary
from src.gmail.models.mail_attachment import MailAttachment
from src.gmail.models.mail_message import MailMessage
from src.gmail.models.mail_summary import MailSummary


class MailConversationMapper:
    def summary(self, mail: MailSummary) -> MessageSummary:
        return MessageSummary(
            message_id=mail.id,
            conversation_id=mail.thread_id,
            title=mail.subject,
            sender=mail.sender,
            date=mail.date,
            snippet=mail.snippet,
            has_attachments=mail.has_attachments,
        )

    def summary_of_message(self, mail: MailMessage) -> MessageSummary:
        return MessageSummary(
            message_id=mail.id,
            conversation_id=mail.thread_id,
            title=mail.subject,
            sender=mail.sender,
            date=mail.date,
            snippet=mail.snippet,
            has_attachments=bool(mail.attachments),
        )

    def message(self, mail: MailMessage) -> ConversationMessage:
        return ConversationMessage(
            message_id=mail.id,
            conversation_id=mail.thread_id,
            title=mail.subject,
            sender=mail.sender,
            recipients=mail.recipients,
            from_owner=mail.sent_by_owner,
            date=mail.date,
            text=mail.body,
            attachments=[self.attachment(item) for item in mail.attachments],
        )

    def attachment(self, attachment: MailAttachment) -> ConversationAttachment:
        return ConversationAttachment(
            attachment_id=attachment.attachment_id,
            name=attachment.filename,
            media_type=attachment.media_type,
            size=attachment.size,
            availability=AttachmentAvailability.AVAILABLE,
        )
