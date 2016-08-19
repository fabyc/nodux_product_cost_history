#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from sql import Column
from sql.aggregate import Max
from sql.conditionals import Coalesce
from sql.functions import Trim, Substring

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateAction
from trytond.pyson import PYSONEncoder
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['ProductCostHistory', 'OpenProductCostHistory']
__metaclass__ = PoolMeta


class ProductCostHistory():
    __name__ = 'product.product.cost_history'

    purchase_price = fields.Numeric('Purchase Price')

    @classmethod
    def __setup__(cls):
        super(ProductCostHistory, cls).__setup__()

    @classmethod
    def table_query(cls):
        pool = Pool()
        Property = pool.get('ir.property')
        Field = pool.get('ir.model.field')
        property_history = Property.__table_history__()
        field = Field.__table__()
        return property_history.join(field,
            condition=field.id == property_history.field
            ).select(Max(Column(property_history, '__id')).as_('id'),
                Max(property_history.create_uid).as_('create_uid'),
                Max(property_history.create_date).as_('create_date'),
                Max(property_history.write_uid).as_('write_uid'),
                Max(property_history.write_date).as_('write_date'),
                Coalesce(property_history.write_date,
                    property_history.create_date).as_('date'),
                Trim(Substring(property_history.res, ',.*'), 'LEADING', ','
                    ).cast(cls.template.sql_type().base).as_('template'),
                Trim(property_history.value, 'LEADING', ','
                    ).cast(cls.cost_price.sql_type().base).as_('cost_price'),
                Trim(property_history.value, 'LEADING', ','
                    ).cast(cls.cost_price.sql_type().base).as_('purchase_price'),
                where=(field.name == 'cost_price')
                & property_history.res.like('product.template,%'),
                group_by=(property_history.id,
                    Coalesce(property_history.write_date,
                        property_history.create_date),
                    property_history.res, property_history.value))

class OpenProductCostHistory():
    'Open Product Cost History'
    __name__ = 'product.product.cost_history.open'

    def do_open(self, action):
        pool = Pool()
        Product = pool.get('product.product')
        origin = Transaction().context['active_ids']

        def in_group():
            pool = Pool()
            ModelData = pool.get('ir.model.data')
            User = pool.get('res.user')
            Group = pool.get('res.group')

            group = Group(ModelData.get_id('nodux_product_cost_history',
                            'group_cost_history'))

            transaction = Transaction()
            user_id = transaction.user
            if user_id == 0:
                user_id = transaction.context.get('user', user_id)
            if user_id == 0:
                return True
            user = User(user_id)

            return origin and group in user.groups

        if not in_group():
            self.raise_user_error("No esta autorizado a revisar el historial de costos")

        active_id = Transaction().context.get('active_id')
        if not active_id or active_id < 0:
            action['pyson_domain'] = PYSONEncoder().encode([
                    ('template', '=', None),
                    ])
        else:
            product = Product(active_id)
            action['pyson_domain'] = PYSONEncoder().encode([
                    ('template', '=', product.template.id),
                    ])
        return action, {}
