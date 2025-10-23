"""Entry point for the kernel wrapper."""

from ipykernel.kernelapp import IPKernelApp
from .kernel import WrapperKernel

if __name__ == '__main__':
    IPKernelApp.launch_instance(kernel_class=WrapperKernel)
