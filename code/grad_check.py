import numpy as np

STUDENT={'name': 'Ofri Kleinfeld',
         'ID': '302893680'}


def gradient_check(f, x):
    """ 
    Gradient check for a function f 
    - f should be a function that takes a single argument and outputs the cost and its gradients
    - x is the point (numpy array) to check the gradient at
    """ 
    fx, grad = f(x)  # Evaluate function value at original point
    h = 1e-4

    # Iterate over all indexes in x
    it = np.nditer(x, flags=['multi_index'], op_flags=['readwrite'])
    while not it.finished:
        ix = it.multi_index

        ### modify x[ix] with h defined above to compute the numerical gradient.
        ### if you change x, make sure to return it back to its original state for the next iteration.
        ### YOUR CODE HERE:
        x_plus_h = np.copy(x)
        x_plus_h[ix] += h
        fx_plus_h, _ = f(x_plus_h)

        x_minus_h = np.copy(x)
        x_minus_h[ix] -= h
        fx_minus_h, _ = f(x_minus_h)

        numeric_gradient = (fx_plus_h - fx_minus_h) / (2 * h)
        ### END YOUR CODE

        # Compare gradients
        reldiff = abs(numeric_gradient - grad[ix]) / max(1, abs(numeric_gradient), abs(grad[ix]))
        if reldiff > 1e-5:
            print("Gradient check failed.")
            print("First gradient error found at index %s" % str(ix))
            print("Your gradient: %f \t Numerical gradient: %f" % (grad[ix], numeric_gradient))
            return
    
        it.iternext()  # Step to next index

    print("Gradient check passed!")


def sanity_check():
    """
    Some basic sanity checks.
    """
    quad = lambda x: (np.sum(x ** 2), x * 2)

    print("Running sanity checks...")
    gradient_check(quad, np.array(123.456))      # scalar test
    gradient_check(quad, np.random.randn(3,))    # 1-D test
    gradient_check(quad, np.random.randn(4, 5))   # 2-D test
    print("")


def tanh_derivative_check():
    from mlp1 import tanh, tanh_derivative

    tanh_f = lambda x: (np.sum(tanh(x)), tanh_derivative(x))

    print("Checking tanh function gradient")
    gradient_check(tanh_f, np.array(123.456))      # scalar test
    gradient_check(tanh_f, np.random.randn(3,))    # 1-D test
    gradient_check(tanh_f, np.random.randn(4, 5))   # 2-D test
    print("")


# def mlp_check():
#     from mlp1 import create_classifier, loss_and_gradients as mlp1_loss_and_grad
#     in_dim, hid_dim, out_dim = 5, 3, 2
#     initialized_params = create_classifier(in_dim=in_dim, hid_dim=hid_dim, out_dim=out_dim)
#
#     def randomly_initialize_params(params):
#         new_params = []
#         for parameter in params:
#             new_params.append(np.random.randn(*parameter.shape))
#         return new_params
#
#     x = [1, 2, 3, 4, 5]
#     y = 0
#     for i in range(len(initialized_params)):
#         # random_params = randomly_initialize_params(initialized_params)
#         W, b, U, b_tag = initialized_params
#
#         def _loss_and_W_grad(W_):
#             loss, grads = mlp1_loss_and_grad(x, y, [W_, b, U, b_tag])
#             return loss, grads[0]
#
#         def _loss_and_b_grad(b_):
#             loss, grads = mlp1_loss_and_grad(x, y, [W, b_, U, b_tag])
#             return loss, grads[1]
#
#         def _loss_and_U_grad(U_):
#             loss, grads = mlp1_loss_and_grad(x, y, [W, b, U_, b_tag])
#             return loss, grads[2]
#
#         def _loss_and_b_tag_grad(b_tag_):
#             loss, grads = mlp1_loss_and_grad(x, y, [W, b, U, b_tag_])
#             return loss, grads[3]
#
#         # gradient_check(_loss_and_W_grad, W)
#         # gradient_check(_loss_and_b_grad, b)
#         gradient_check(_loss_and_U_grad, U)
#         gradient_check(_loss_and_b_tag_grad, b_tag)


if __name__ == '__main__':
    # If these fail, your code is definitely wrong.
    sanity_check()
    tanh_derivative_check()
    # mlp_check()
