from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from orders.models import Order
from io import BytesIO
import braintree
import weasyprint


def payment_process(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)

    if request.method=='POST':
        #retrieve nonce
        nonce = request.POST.get('payment_method_nonce', None)
        #create and submit transaction
        result = braintree.Transaction.sale({
            'amount': '{:.2f}'.format(order.get_total_cost()),
            'payment_method_nonce':nonce,
            'options': {
                'submit_for_settlement':True
            }
        })
        if result.is_success:
            #mark the order paid
            order.paid = True
            #store the unique transaction id
            order.braintree_id = result.transaction.id
            order.save()
            subject = 'My shop - invoice no. {}'.format(order.id)
            message = 'Please, find attached the invoice for your\
                    purchase.'
            email = EmailMessage(subject,
                                message,
                                'admin@myshop.com',
                                [order.email])
            html = render_to_string('orders/order.pdf.html', 
                                {"order": order})
            out = BytesIO()
            stylesheets = [weasyprint.CSS(settings.STATIC_ROOT + 
                                    'css/pdf.css')]
            weasyprint.HTML(string=html).write_pdf(out, 
                            stylesheets=stylesheets)
            email.attach('order_{}.pdf'.format(order.id),
                            out.getvalue(),
                            'application/pdf')
            email.send()

            return redirect('payment:done')
        else:
            return redirect('payment:canceled')
    else:
        #generate token
        client_token = braintree.ClientToken.generate()
        return render(request,
                    'payment/process.html',
                    {'order':order,
                    'client_token':client_token})


def payment_done(request):
    return render(request, 'payment/done.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')
    