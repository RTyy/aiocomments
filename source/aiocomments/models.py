"""AIOComments Models."""
from datetime import datetime
from sqlalchemy import text

from core.collections import Enum
from core.db.models import Model
from core.db import fields as f


class DlRequest(Model):
    """Downalod Request Model."""

    class Format(Enum):
        """Supported Report Formats."""

        XML = 0, 'xml'

    class State(Enum):
        """Request States."""

        VALID = 0, 'Valid'
        INVALID = 1, 'Invalid'

    itype_id = f.Integer()
    i_id = f.Integer()
    author_id = f.Integer(index=True)
    start = f.DateTime(with_timezone=True)
    end = f.DateTime(with_timezone=True)
    # file format: 0 - XML
    fmt = f.Integer(nullable=False, default=Format.XML)
    state = f.Integer(default=State.INVALID)
    filename = f.String()
    created = f.DateTime(with_timezone=True, nullable=False,
                         default=datetime.utcnow)

    class Meta:
        """Meta Descriptions."""

        # Indexes
        index = (
            ('ix_generic_tree_id', 'itype_id', 'i_id'),
            ('ix_dates', 'start', 'end'),
        )
        # Unique
        unique = (
            ('itype_id', 'i_id', 'author_id', 'start', 'end', 'fmt'),
        )

    def save(self, db, fs, *args, **kwargs):
        """Save override."""
        if not self.pk:
            self.created = datetime.utcnow()
            # generate report filename
            self.filename = fs.generate_filename(
                ext=DlRequest.Format[self.fmt].verbose)

        return super().save(db, *args, **kwargs)


class UserDlRequest(Model):
    """Users vs Download Requests."""

    user_id = f.Integer(nullable=False, index=True)
    dlrequest_id = f.ForeignKey(DlRequest.id)
    created = f.DateTime(with_timezone=True, nullable=False,
                         default=datetime.utcnow)

    # Unique
    unique = (
        ('user_id', 'dlrequest_id'),
    )


class Instance(Model):
    """Model to store info about commented instances."""

    itype_id = f.Integer(nullable=False, default=0)
    i_id = f.Integer(nullable=False)
    children_cnt = f.Integer(f.CheckConstraint('children_cnt >= 0'),
                             nullable=False, default=0)
    lft_ins_num = f.Integer(f.CheckConstraint('lft_ins_num >= 0'),
                            nullable=False, default=0)
    lft_ins_den = f.Integer(f.CheckConstraint('lft_ins_den > 0'),
                            nullable=False, default=1)
    scale = -1

    class Meta:
        """Meta Descriptions."""

        # # Indexes
        # index = (
        #     ('ix_generic_tree_id', 'itype_id', 'i_id'),
        # )
        # Unique
        unique = (
            ('itype_id', 'i_id'),
        )

    @property
    def tree_id(self):
        """Return tree_id of the instance."""
        return self.pk


class Comment(Model):
    """Model to store Comments as collection of the trees.

    Tree hierarchy based on Farey Sequence stratagy.
    """

    itype_id = f.Integer(nullable=False, default=0)
    i_id = f.Integer(nullable=False)
    author_id = f.Integer(nullable=False, index=True)
    content = f.Text(nullable=False)
    created = f.DateTime(with_timezone=True, nullable=False,
                         default=datetime.utcnow)
    updated = f.DateTime(with_timezone=True, nullable=False,
                         default=datetime.utcnow)

    tree_id = f.ForeignKey(Instance.id, index=True)
    parent_id = f.ForeignKey('comment.id', index=True)
    children_cnt = f.Integer(f.CheckConstraint('children_cnt >= 0'),
                             nullable=False, default=0)
    scale = f.Integer(f.CheckConstraint('scale >= 0'),
                      default=0, nullable=False)

    # Farey sequence based tree fields
    lft_num = f.Integer(f.CheckConstraint('lft_num >= 0'), nullable=False)
    lft_den = f.Integer(f.CheckConstraint('lft_den > 0'), nullable=False)
    rht_num = f.Integer(f.CheckConstraint('rht_num > 0'), nullable=False)
    rht_den = f.Integer(f.CheckConstraint('rht_den > 0'), nullable=False)
    lft_ins_num = f.Integer(f.CheckConstraint('lft_ins_num >= 0'),
                            nullable=False)
    lft_ins_den = f.Integer(f.CheckConstraint('lft_ins_den > 0'),
                            nullable=False)

    class Meta:
        """Meta Descriptions."""

        # Indexes
        index = (
            ('ix_hierarhy_tree', 'tree_id', 'scale',
             text('(lft_num/lft_den::float)')),
            ('ix_tree_level', 'tree_id', 'parent_id'),
        )

    @property
    def lft(self):
        """Node left key calculator."""
        return self.lft_num / self.lft_den

    @property
    def rht(self):
        """Node right key calculator."""
        return self.rht_num / self.rht_den

    @classmethod
    async def tree(self, db, i_id, itype_id=0):
        """Return a tree loaded from the database."""
        if itype_id == 0:
            # make a filter to get all the childern comments
            root = await Comment.list(db).get(Comment.id == i_id)
            flt = (Comment.tree_id == root.tree_id) & \
                  (Comment.scale > root.scale) & \
                  (text('lft_num/lft_den::float >= %s' % root.lft) &
                   text('lft_num/lft_den::float < %s' % root.rht))
        else:
            # make a filter for the full tree of the external instance
            root = await Instance.list(db).get((Instance.i_id == i_id) &
                                               (Instance.itype_id == itype_id))
            flt = Comment.tree_id == root.id

        childern = Comment.list(db).filter(flt) \
            .order_by(text('lft_num/lft_den::float'), Comment.scale)

        return root, childern

    async def delete(self, db):
        """Delete a tree branch."""
        if self.parent_id:
            parent = await Comment.list(db).get(Comment.id == self.parent_id)
        else:
            parent = await Instance.list(db).get(Instance.id == self.tree_id)

        # set parent's medaint base
        if self.rht_num == parent.lft_ins_num \
                and self.rht_den == parent.lft_ins_den:
            parent.lft_ins_num = self.lft_num
            parent.lft_ins_den = self.lft_den

        # delete full branch including this comment
        flt = text('lft_num/lft_den::float >= %s' % self.lft) \
            & text('lft_num/lft_den::float < %s' % self.rht)

        rows_count = await Comment.list(db).delete(
            (Comment.tree_id == self.tree_id) & flt &
            (Comment.scale >= self.scale))

        setattr(self, type(self)._meta.pk, None)

        # update parent children_cnt
        parent.children_cnt -= 1
        await parent.save(db)

        return rows_count

    async def save(self, db):
        """Calculate node keys and do saving stuff."""
        if not self.pk:
            # add comment to the tree
            # if instance type is not a Comment
            # get/create an instance object for it.
            if not self.itype_id == 0:
                # !Important: Instance will be a "root" for a comments tree
                try:
                    # try to get tree for the instance
                    parent = await Instance.list(db).get(
                        (Instance.itype_id == self.itype_id) &
                        (Instance.i_id == self.i_id))

                except Instance.DoesNotExist:
                    # make new tree for the instance
                    parent = Instance(itype_id=self.itype_id,
                                      i_id=self.i_id)
                    await parent.save(db)

                self.scale = 0
                self.tree_id = parent.id

                # calculate new mediant
                med_num = parent.lft_ins_num + 1  # root rht_num is always 1
                med_den = parent.lft_ins_den + 1  # root rht_den is always 1

            else:
                parent = await Comment.list(db).get(Comment.id == self.i_id)
                self.parent_id = parent.id
                self.scale = parent.scale + 1
                self.tree_id = parent.tree_id

                # calculate new mediant
                med_num = parent.lft_ins_num + parent.rht_num
                med_den = parent.lft_ins_den + parent.rht_den

            # new node left key
            self.lft_num = parent.lft_ins_num
            self.lft_den = parent.lft_ins_den

            # new node mediant
            self.lft_ins_num = parent.lft_ins_num
            self.lft_ins_den = parent.lft_ins_den

            # new node right key
            self.rht_num = med_num
            self.rht_den = med_den

            # update parent mediant with the calculated one
            parent.lft_ins_num = med_num
            parent.lft_ins_den = med_den

            # try to save a new comment
            await super().save(db)
            # update parent comment
            parent.children_cnt += 1
            await parent.save(db)

        else:
            # renew update date
            self.updated = datetime.utcnow()
            await super().save(db)


class EventLog(Model):
    """Model to store events triggered by operations on comments."""

    class EventType(Enum):
        """Event Types."""

        CREATED = 0, 'Created'
        CHANGED = 1, 'Changed'
        DELETED = 2, 'Deleted'

    user_id = f.Integer(nullable=False)
    tree_id = f.Integer(nullable=False, index=True)
    author_id = f.Integer(nullable=False, index=True)
    comment_id = f.Integer(nullable=False, index=True)
    comment_cdate = f.DateTime(with_timezone=True, nullable=False)
    e_type = f.Integer(nullable=False, default=EventType.CREATED)
    e_date = f.DateTime(with_timezone=True, nullable=False,
                        default=datetime.utcnow)

    class Meta:
        """Meta Descriptions."""

        # Indexes
        index = (
            ('ix_tree_events', 'tree_id', 'e_date'),
            ('ix_author_events', 'author_id', 'e_date'),
            ('ix_tree_author_events', 'tree_id', 'author_id', 'e_date'),
        )

    async def save(self, *args, **kwargs):
        """Save event.

        Set default event date.
        """
        if not self.pk:
            self.e_date = datetime.utcnow()

        return await super().save(*args, **kwargs)
