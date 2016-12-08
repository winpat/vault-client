package main

import (
	"fmt"
	"os"
	"strings"
	"testing"

	"github.com/mitchellh/cli"
)

func TestDelete(t *testing.T) {

	err := LoadConfig()
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
	}

	err = InitializeClient(cfg)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
	}

	ui := new(cli.MockUi)
	c := &DeleteCommand{Ui: ui}

	t.Run("TooManyArgs", func(t *testing.T) {

		args := []string{
			"secret/doesntexist",
			"secret/toomucharguments",
		}

		if rc := c.Run(args); rc != 1 {
			t.Fatalf("Wrong exit code. errors: \n%s", ui.ErrorWriter.String())
		}

		expected := "The rm command expects at most one argument"
		if actual := ui.ErrorWriter.String(); !strings.Contains(actual, expected) {
			t.Fatalf("expected:\n%s\n\nto include: %q", actual, expected)
		}
	})

	t.Run("NonexistentSecret", func(t *testing.T) {

		args := []string{"secret/doesntexist"}

		if rc := c.Run(args); rc != 1 {
			t.Fatalf("Wrong exit code. errors: \n%s", ui.ErrorWriter.String())
		}

		expected := "Secret does not exist"
		if actual := ui.ErrorWriter.String(); !strings.Contains(actual, expected) {
			t.Fatalf("expected:\n%s\n\nto include: %q", actual, expected)
		}
	})

	t.Run("ExistentSecret", func(t *testing.T) {

		// Create test secret
		data := make(map[string]interface{})
		data["key"] = "value"

		_, err = vc.Logical().Write("secret/existent", data)
		if err != nil {
			t.Fatalf("Unable to write test secret: %q", err)
		}

		ui := new(cli.MockUi)
		c := &DeleteCommand{Ui: ui}

		args := []string{"secret/existent"}

		if rc := c.Run(args); rc != 0 {
			t.Fatalf("Wrong exit code. errors: \n%s", ui.ErrorWriter.String())
		}

		expected := ""
		if actual := ui.ErrorWriter.String(); !strings.Contains(actual, expected) {
			t.Fatalf("expected:\n%s\n\nto include: %q", actual, expected)
		}

	})
}