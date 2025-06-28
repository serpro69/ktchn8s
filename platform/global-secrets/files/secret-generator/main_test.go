package main

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/kubernetes/fake"
	k8stesting "k8s.io/client-go/testing"
)

type MockSecrets struct {
	mock.Mock
}

func (m *MockSecrets) Get(ctx context.Context, name string, opts metav1.GetOptions) (*v1.Secret, error) {
	args := m.Called(ctx, name, opts)
	return args.Get(0).(*v1.Secret), args.Error(1)
}

func (m *MockSecrets) Create(ctx context.Context, secret *v1.Secret, opts metav1.CreateOptions) (*v1.Secret, error) {
	args := m.Called(ctx, secret, opts)
	return args.Get(0).(*v1.Secret), args.Error(1)
}

func (m *MockSecrets) Update(ctx context.Context, secret *v1.Secret, opts metav1.UpdateOptions) (*v1.Secret, error) {
	args := m.Called(ctx, secret, opts)
	return args.Get(0).(*v1.Secret), args.Error(1)
}

func TestCreateOrUpdateSecret_Create(t *testing.T) {
	randomSecrets, err := readConfigFile("config_test.yaml")
	assert.NoError(t, err)

	clientset := fake.NewSimpleClientset()
	clientset.Fake.PrependReactor("get", "secrets", func(action k8stesting.Action) (handled bool, ret runtime.Object, err error) {
		return true, nil, errors.NewNotFound(v1.Resource("secrets"), "test-secret")
	})

	clientset.Fake.PrependReactor("create", "secrets", func(action k8stesting.Action) (handled bool, ret runtime.Object, err error) {
		return true, &v1.Secret{}, nil
	})

	err = createOrUpdateSecret(clientset, "test-secret", randomSecrets[0])
	assert.NoError(t, err)

	// Check that create was called
	assert.True(t, len(clientset.Actions()) > 1 && clientset.Actions()[1].GetVerb() == "create", "Create should be called")
}

func TestCreateOrUpdateSecret_Update(t *testing.T) {
	randomSecrets, err := readConfigFile("config_test.yaml")
	assert.NoError(t, err)

	existingSecret := &v1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-secret",
			Namespace: namespace,
		},
		Data: map[string][]byte{
			"key1": []byte("existingpassword"),
		},
	}

	clientset := fake.NewSimpleClientset(existingSecret)
	clientset.Fake.PrependReactor("update", "secrets", func(action k8stesting.Action) (handled bool, ret runtime.Object, err error) {
		return true, &v1.Secret{}, nil
	})

	err = createOrUpdateSecret(clientset, "test-secret", randomSecrets[0])
	assert.NoError(t, err)

	// Check that update was called
	assert.True(t, len(clientset.Actions()) > 1 && clientset.Actions()[1].GetVerb() == "update", "Update should be called")
}

func TestCreateOrUpdateSecret_NoChanges(t *testing.T) {
	randomSecrets, err := readConfigFile("config_test.yaml")
	assert.NoError(t, err)

	existingSecret := &v1.Secret{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-secret",
			Namespace: namespace,
		},
		Data: map[string][]byte{
			"key1": []byte("existingpassword"),
			"key2": []byte("anotherpassword"),
		},
	}

	clientset := fake.NewSimpleClientset(existingSecret)

	err = createOrUpdateSecret(clientset, "test-secret", randomSecrets[0])
	assert.NoError(t, err)

	// Check that no update was called
	assert.False(t, len(clientset.Actions()) > 1 && clientset.Actions()[1].GetVerb() == "update", "Update should not be called")
}
